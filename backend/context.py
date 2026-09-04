"""Context assembly: turn files, diffs and repo metadata into a prompt."""

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from .profiles import Profile


@dataclass
class ContextBlock:
    """One labelled chunk of context handed to the council."""

    label: str
    content: str
    language: str = ""


def read_file_block(path: str) -> ContextBlock:
    """Read a file into a context block. Raises if unreadable."""
    p = Path(path)
    text = p.read_text(encoding="utf-8", errors="replace")
    return ContextBlock(label=str(p), content=text, language=p.suffix.lstrip("."))


def git_diff_block(ref: Optional[str] = None, cwd: Optional[str] = None) -> Optional[ContextBlock]:
    """Capture `git diff` (optionally against a ref) as a context block."""
    cmd = ["git", "diff"]
    if ref:
        cmd.append(ref)
    try:
        out = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True, timeout=30, check=False
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0 or not out.stdout.strip():
        return None
    return ContextBlock(
        label=f"git diff{' ' + ref if ref else ''}", content=out.stdout, language="diff"
    )


def repo_info_block(cwd: Optional[str] = None) -> Optional[ContextBlock]:
    """Repo name + branch, so the council knows where it is."""

    def _git(*args: str) -> Optional[str]:
        try:
            out = subprocess.run(
                ["git", *args], cwd=cwd, capture_output=True, text=True,
                timeout=10, check=False,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        return out.stdout.strip() if out.returncode == 0 else None

    root = _git("rev-parse", "--show-toplevel")
    if not root:
        return None
    branch = _git("rev-parse", "--abbrev-ref", "HEAD") or "unknown"
    return ContextBlock(
        label="repository", content=f"name: {Path(root).name}\nbranch: {branch}"
    )


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    keep = limit // 2
    cut = len(text) - limit
    return f"{text[:keep]}\n\n[... {cut} Zeichen gekuerzt ...]\n\n{text[-keep:]}"


def build_prompt(
    question: str,
    context_blocks: Optional[List[ContextBlock]] = None,
    profile: Optional[Profile] = None,
) -> str:
    """Compose the message every council member receives.

    Context first, question last, so the question stays the most recent thing
    the model reads. Blocks share the profile's character budget evenly.
    """
    blocks = [b for b in (context_blocks or []) if b.content.strip()]
    if not blocks:
        return question

    budget = profile.max_context_chars if profile else 60000
    per_block = max(2000, budget // len(blocks))

    parts = ["# Kontext\n"]
    for block in blocks:
        body = _truncate(block.content, per_block)
        fence = f"```{block.language}" if block.language else "```"
        parts.append(f"## {block.label}\n{fence}\n{body}\n```\n")
    parts.append(f"# Frage\n{question}")
    return "\n".join(parts)
