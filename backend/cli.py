"""Headless entry point: run the council from any repository."""

import argparse
import asyncio
import json
import sys
import uuid
from pathlib import Path
from typing import List, Optional

from . import storage
from .config import MissingAPIKeyError
from .context import ContextBlock, git_diff_block, read_file_block, repo_info_block
from .council import generate_conversation_title, run_full_council
from .export import DEFAULT_ADR_DIR, write_adr
from .openrouter import OpenRouterAuthError
from .profiles import DEFAULT_PROFILE, PROFILES, get_profile


def _gather_context(args) -> List[ContextBlock]:
    blocks: List[ContextBlock] = []

    if not args.no_repo_info:
        repo = repo_info_block()
        if repo:
            blocks.append(repo)

    for path in args.file or []:
        try:
            blocks.append(read_file_block(path))
        except OSError as e:
            print(f"warn: cannot read {path}: {e}", file=sys.stderr)

    if args.diff is not None:
        diff = git_diff_block(args.diff or None)
        if diff:
            blocks.append(diff)
        else:
            print("warn: no diff to include", file=sys.stderr)

    if args.stdin and not sys.stdin.isatty():
        piped = sys.stdin.read()
        if piped.strip():
            blocks.append(ContextBlock(label="stdin", content=piped))

    return blocks


def _format_report(question, stage1, stage2, stage3, metadata, profile_name) -> str:
    stats = metadata.get("run_stats", {}) or {}
    lines = [stage3.get("response", "").strip(), ""]

    ranking = metadata.get("aggregate_rankings") or []
    if ranking:
        lines += ["---", "", "**Peer-Ranking** (Ø Position, kleiner ist besser):", ""]
        lines += [
            f"- {r['model']} — {r['average_rank']} ({r['rankings_count']} Stimmen)"
            for r in ranking
        ]
        lines.append("")

    failed = stats.get("failed_calls", 0)
    lines += [
        "---",
        (
            f"Profil `{profile_name}` · {len(stage1)} Antworten · "
            f"{stats.get('duration_s', 0)}s · ${stats.get('cost_usd', 0)} · "
            f"{stats.get('prompt_tokens', 0)}+{stats.get('completion_tokens', 0)} Tokens"
            + (f" · {failed} fehlgeschlagene Calls" if failed else "")
        ),
    ]
    return "\n".join(lines)


async def _run_ask(args) -> int:
    profile = get_profile(args.profile)
    blocks = _gather_context(args)

    if not args.quiet:
        print(
            f"Konzil laeuft: Profil '{profile.name}', {len(profile.models)} Modelle, "
            f"~{profile.expected_calls} Calls, {profile.expected_latency} ...",
            file=sys.stderr,
        )

    stage1, stage2, stage3, metadata = await run_full_council(
        args.question, profile=profile, context_blocks=blocks
    )

    if not stage1:
        print("Alle Modelle sind ausgefallen.", file=sys.stderr)
        return 1

    conversation_id = str(uuid.uuid4())
    storage.create_conversation(conversation_id)
    title = await generate_conversation_title(args.question)
    storage.update_conversation_title(conversation_id, title)
    storage.add_user_message(conversation_id, args.question)
    storage.add_assistant_message(conversation_id, stage1, stage2, stage3, metadata)
    metadata["conversation_id"] = conversation_id
    metadata["title"] = title

    if args.json:
        output = json.dumps(
            {
                "question": args.question,
                "stage1": stage1,
                "stage2": stage2,
                "stage3": stage3,
                "metadata": metadata,
            },
            indent=2,
            ensure_ascii=False,
        )
    else:
        output = _format_report(
            args.question, stage1, stage2, stage3, metadata, profile.name
        )

    if args.out:
        Path(args.out).write_text(output, encoding="utf-8")
        print(f"geschrieben: {args.out}", file=sys.stderr)
    else:
        print(output)

    if args.adr:
        path = write_adr(
            args.question, stage3, metadata, stage1,
            adr_dir=args.adr_dir, title=title,
        )
        print(f"ADR: {path}", file=sys.stderr)

    if not args.quiet:
        print(f"Run gespeichert: {conversation_id}", file=sys.stderr)
    return 0


def _cmd_profiles(_args) -> int:
    for name, profile in PROFILES.items():
        marker = " (default)" if name == DEFAULT_PROFILE else ""
        print(f"{name}{marker}")
        print(f"  {profile.description}")
        print(f"  Modelle:  {', '.join(profile.models)}")
        print(f"  Chairman: {profile.chairman}")
        print(
            f"  Peer-Review: {'ja' if profile.peer_review else 'nein'} · "
            f"~{profile.expected_calls} Calls · {profile.expected_latency}"
        )
        print()
    return 0


def _cmd_log(args) -> int:
    conversations = storage.list_conversations()[: args.last]
    if not conversations:
        print("Noch keine Runs gespeichert.")
        return 0
    for c in conversations:
        print(f"{c['created_at'][:19]}  {c['id'][:8]}  {c['title']}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="council",
        description="Ask a council of LLMs a question from any repository.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    ask = sub.add_parser("ask", help="run the council on a question")
    ask.add_argument("question", help="the question to deliberate")
    ask.add_argument(
        "--profile", default=DEFAULT_PROFILE, choices=sorted(PROFILES),
        help=f"council profile (default: {DEFAULT_PROFILE})",
    )
    ask.add_argument(
        "--file", action="append", metavar="PATH",
        help="include a file as context (repeatable)",
    )
    ask.add_argument(
        "--diff", nargs="?", const="", metavar="REF",
        help="include `git diff [REF]` as context",
    )
    ask.add_argument("--stdin", action="store_true", help="include piped stdin as context")
    ask.add_argument("--no-repo-info", action="store_true", help="omit repo name/branch")
    ask.add_argument("--out", metavar="FILE", help="write the answer to a file")
    ask.add_argument("--json", action="store_true", help="emit the full run as JSON")
    ask.add_argument("--adr", action="store_true", help="also write an ADR markdown file")
    ask.add_argument("--adr-dir", default=DEFAULT_ADR_DIR, help="ADR target directory")
    ask.add_argument("--quiet", action="store_true", help="suppress progress output")
    ask.set_defaults(func=lambda a: asyncio.run(_run_ask(a)))

    profiles = sub.add_parser("profiles", help="list available council profiles")
    profiles.set_defaults(func=_cmd_profiles)

    log = sub.add_parser("log", help="list recent council runs")
    log.add_argument("--last", type=int, default=20, help="how many runs to show")
    log.set_defaults(func=_cmd_log)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (MissingAPIKeyError, OpenRouterAuthError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
