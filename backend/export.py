"""Export a council run as an ADR (architecture decision record) markdown file."""

import re
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

DEFAULT_ADR_DIR = "docs/decisions"


def slugify(text: str, max_len: int = 60) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return (slug[:max_len].rstrip("-")) or "decision"


def next_index(adr_dir: Path) -> int:
    """Next free 4-digit ADR number in the directory."""
    highest = 0
    if adr_dir.is_dir():
        for path in adr_dir.glob("[0-9][0-9][0-9][0-9]-*.md"):
            try:
                highest = max(highest, int(path.name[:4]))
            except ValueError:
                continue
    return highest + 1


def render_adr(
    question: str,
    stage3: Dict[str, Any],
    metadata: Dict[str, Any],
    stage1: Optional[List[Dict[str, Any]]] = None,
    title: Optional[str] = None,
) -> str:
    """Render the ADR markdown body."""
    stats = metadata.get("run_stats", {}) or {}
    models = [r.get("model") for r in (stage1 or [])]
    ranking = metadata.get("aggregate_rankings") or []

    lines = [
        "---",
        f"date: {date.today().isoformat()}",
        "status: proposed",
        f"profile: {metadata.get('profile', 'unknown')}",
        f"chairman: {stage3.get('model', 'unknown')}",
        f"council: [{', '.join(m for m in models if m)}]",
        f"cost_usd: {stats.get('cost_usd', 0)}",
        f"duration_s: {stats.get('duration_s', 0)}",
        "source: llm-council",
        "---",
        "",
        f"# {title or question.strip().splitlines()[0][:80]}",
        "",
        "## Frage",
        "",
        question.strip(),
        "",
        "## Antwort des Konzils",
        "",
        (stage3.get("response") or "").strip(),
        "",
    ]

    if metadata.get("context_labels"):
        lines += [
            "## Kontext, den das Konzil gesehen hat",
            "",
            *[f"- `{label}`" for label in metadata["context_labels"]],
            "",
        ]

    if ranking:
        lines += [
            "## Peer-Ranking (Durchschnittsposition, kleiner ist besser)",
            "",
            "| Modell | Ø Position | Stimmen |",
            "| --- | --- | --- |",
            *[
                f"| {r['model']} | {r['average_rank']} | {r['rankings_count']} |"
                for r in ranking
            ],
            "",
            "> Das Ranking misst, wie die Modelle einander bewerten - nicht Korrektheit.",
            "",
        ]

    return "\n".join(lines)


def write_adr(
    question: str,
    stage3: Dict[str, Any],
    metadata: Dict[str, Any],
    stage1: Optional[List[Dict[str, Any]]] = None,
    adr_dir: str = DEFAULT_ADR_DIR,
    title: Optional[str] = None,
) -> Path:
    """Write the ADR into the target repo and return its path."""
    directory = Path(adr_dir)
    directory.mkdir(parents=True, exist_ok=True)
    index = next_index(directory)
    path = directory / f"{index:04d}-{slugify(title or question)}.md"
    path.write_text(
        render_adr(question, stage3, metadata, stage1, title), encoding="utf-8"
    )
    return path
