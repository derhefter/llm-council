"""MCP server: expose the LLM Council as a tool in every Claude Code session.

Deep runs take 1-3 minutes, which is longer than most MCP clients will wait on
a single tool call. So the deep path is split: council_start returns a run_id
immediately, council_result polls it. council_ask stays blocking for the quick
profile only.
"""

import asyncio
import uuid
from typing import Any, Dict, List, Optional

from mcp.server.mcpserver import MCPServer

from . import storage
from .context import ContextBlock, read_file_block
from .council import generate_conversation_title, run_full_council
from .export import DEFAULT_ADR_DIR, write_adr
from .profiles import DEFAULT_PROFILE, PROFILES, get_profile

mcp = MCPServer("council", instructions=(
    "Ask a council of several LLMs a question. Worth it only when the question "
    "is expensive to get wrong, has no cheap ground truth, and model diversity "
    "buys coverage. Start with council_profiles if unsure."
))

# run_id -> {"task": asyncio.Task, "question": str, "profile": str}
_RUNS: Dict[str, Dict[str, Any]] = {}


def _build_blocks(
    context: Optional[str], files: Optional[List[str]]
) -> List[ContextBlock]:
    blocks: List[ContextBlock] = []
    if context and context.strip():
        blocks.append(ContextBlock(label="context", content=context))
    for path in files or []:
        try:
            blocks.append(read_file_block(path))
        except OSError as e:
            blocks.append(
                ContextBlock(label=path, content=f"[could not read this file: {e}]")
            )
    return blocks


async def _execute(question: str, profile_name: str, blocks: List[ContextBlock]) -> Dict[str, Any]:
    profile = get_profile(profile_name)
    stage1, stage2, stage3, metadata = await run_full_council(
        question, profile=profile, context_blocks=blocks
    )

    if not stage1:
        return {"status": "failed", "error": "All council models failed to respond."}

    conversation_id = str(uuid.uuid4())
    storage.create_conversation(conversation_id)
    title = await generate_conversation_title(question)
    storage.update_conversation_title(conversation_id, title)
    storage.add_user_message(conversation_id, question)
    storage.add_assistant_message(conversation_id, stage1, stage2, stage3, metadata)

    return {
        "status": "complete",
        "title": title,
        "conversation_id": conversation_id,
        "profile": profile.name,
        "answer": stage3.get("response", ""),
        "chairman": stage3.get("model"),
        "responders": [r["model"] for r in stage1],
        "aggregate_ranking": metadata.get("aggregate_rankings", []),
        "run_stats": metadata.get("run_stats", {}),
        "context_labels": metadata.get("context_labels", []),
    }


@mcp.tool()
def council_profiles() -> List[Dict[str, Any]]:
    """List the available council profiles with their cost and latency profile.

    Call this when unsure which profile fits: 'quick' for a cheap second
    opinion, 'decision' for architecture/technical decisions, 'research' for
    open questions.
    """
    return [
        {
            "name": p.name,
            "description": p.description,
            "models": p.models,
            "chairman": p.chairman,
            "peer_review": p.peer_review,
            "expected_calls": p.expected_calls,
            "expected_latency": p.expected_latency,
            "default": p.name == DEFAULT_PROFILE,
        }
        for p in PROFILES.values()
    ]


@mcp.tool()
async def council_start(
    question: str,
    profile: str = DEFAULT_PROFILE,
    context: Optional[str] = None,
    files: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Start a council deliberation in the background and return a run_id.

    Use this for the 'decision' and 'research' profiles - they take 1-3 minutes.
    Poll council_result(run_id) afterwards.

    Only worth calling when the question is expensive to get wrong, has no cheap
    ground truth (no test or benchmark settles it), and model diversity plausibly
    buys coverage. Otherwise answer it yourself.

    Args:
        question: The question, stated so it stands on its own.
        profile: quick | decision | research
        context: Free-form context (constraints, prior decisions, snippets).
        files: Absolute paths to include verbatim as context.
    """
    get_profile(profile)  # validate early
    blocks = _build_blocks(context, files)
    run_id = uuid.uuid4().hex[:12]
    task = asyncio.create_task(_execute(question, profile, blocks))
    _RUNS[run_id] = {"task": task, "question": question, "profile": profile}
    return {
        "run_id": run_id,
        "status": "running",
        "hint": "Poll council_result(run_id). Expect "
                f"{get_profile(profile).expected_latency}.",
    }


@mcp.tool()
async def council_result(run_id: str) -> Dict[str, Any]:
    """Fetch the result of a council run started with council_start.

    Returns status 'running' while the council deliberates, 'complete' with the
    answer once done, or 'failed' with an error.
    """
    run = _RUNS.get(run_id)
    if run is None:
        return {"status": "unknown", "error": f"No run with id {run_id}."}

    task: asyncio.Task = run["task"]
    if not task.done():
        return {"status": "running", "question": run["question"], "profile": run["profile"]}

    try:
        result = task.result()
    except Exception as e:  # noqa: BLE001 - surface the failure to the caller
        return {"status": "failed", "error": f"{type(e).__name__}: {e}"}

    result["run_id"] = run_id
    return result


@mcp.tool()
async def council_ask(
    question: str,
    context: Optional[str] = None,
    files: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Ask the council with the 'quick' profile and wait for the answer.

    Two models, no peer review, ~20-40s. Use this for a cheap second opinion.
    For real decisions use council_start with the 'decision' profile.
    """
    return await _execute(question, "quick", _build_blocks(context, files))


@mcp.tool()
def council_write_adr(
    run_id: str,
    adr_dir: str = DEFAULT_ADR_DIR,
) -> Dict[str, Any]:
    """Write a finished council run into the current repo as an ADR markdown file.

    Call this after council_result returned status 'complete' and the user wants
    the decision recorded.
    """
    run = _RUNS.get(run_id)
    if run is None or not run["task"].done():
        return {"error": f"Run {run_id} is not finished."}

    result = run["task"].result()
    if result.get("status") != "complete":
        return {"error": "Run did not complete successfully."}

    conversation = storage.get_conversation(result["conversation_id"])
    message = conversation["messages"][-1]
    path = write_adr(
        run["question"],
        message["stage3"],
        message.get("metadata", {}),
        message["stage1"],
        adr_dir=adr_dir,
        title=result.get("title"),
    )
    return {"path": str(path)}


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
