"""ADR export: numbering, frontmatter, content."""

from backend.export import next_index, render_adr, slugify, write_adr

STAGE1 = [{"model": "m1", "response": "x"}, {"model": "m2", "response": "y"}]
STAGE3 = {"model": "chair", "response": "## Empfehlung\nNimm A."}
META = {
    "profile": "decision",
    "aggregate_rankings": [
        {"model": "m2", "average_rank": 1.0, "rankings_count": 2},
        {"model": "m1", "average_rank": 2.0, "rankings_count": 2},
    ],
    "context_labels": ["notiz.md"],
    "run_stats": {"cost_usd": 0.42, "duration_s": 95.0},
}


def test_slugify_produces_a_filename_safe_stem():
    assert slugify("Soll ich A oder B?") == "soll-ich-a-oder-b"
    assert slugify("!!!") == "decision", "never produce an empty stem"
    assert len(slugify("wort " * 50)) <= 60


def test_next_index_starts_at_one_and_counts_up(tmp_path):
    assert next_index(tmp_path) == 1

    (tmp_path / "0001-eins.md").write_text("x")
    (tmp_path / "0007-sieben.md").write_text("x")
    (tmp_path / "notiz.md").write_text("x")  # ignored
    assert next_index(tmp_path) == 8


def test_frontmatter_carries_the_run_facts():
    adr = render_adr("Frage?", STAGE3, META, STAGE1, title="Titel")

    assert adr.startswith("---\n")
    for line in ("profile: decision", "chairman: chair",
                 "cost_usd: 0.42", "duration_s: 95.0"):
        assert line in adr
    assert "council: [m1, m2]" in adr


def test_body_carries_question_answer_context_and_ranking():
    adr = render_adr("Frage?", STAGE3, META, STAGE1, title="Titel")

    assert "# Titel" in adr
    assert "## Frage" in adr and "Frage?" in adr
    assert "Nimm A." in adr
    assert "`notiz.md`" in adr
    assert "| m2 | 1.0 | 2 |" in adr
    assert "nicht Korrektheit" in adr, "the ranking caveat must ship with the ADR"


def test_ranking_section_is_omitted_when_there_was_none():
    meta = dict(META, aggregate_rankings=[])
    adr = render_adr("Frage?", STAGE3, meta, STAGE1)

    assert "Peer-Ranking" not in adr


def test_write_adr_creates_the_directory_and_returns_the_path(tmp_path):
    target = tmp_path / "docs" / "decisions"
    path = write_adr("Frage?", STAGE3, META, STAGE1,
                     adr_dir=str(target), title="Mein Titel")

    assert path.exists()
    assert path.name == "0001-mein-titel.md"
    assert "Nimm A." in path.read_text(encoding="utf-8")
