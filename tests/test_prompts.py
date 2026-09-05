"""What reaches the models: context assembly, rubric, output schema."""

from backend.context import ContextBlock, build_prompt
from backend.council import build_chairman_prompt, build_ranking_prompt
from backend.profiles import PROFILES, get_profile

DECISION = get_profile("decision")
QUICK = get_profile("quick")

STAGE1 = [
    {"model": "m1", "response": "Antwort eins"},
    {"model": "m2", "response": "Antwort zwei"},
]


def test_question_stands_alone_without_context():
    assert build_prompt("Warum?", [], DECISION) == "Warum?"


def test_context_precedes_the_question():
    block = ContextBlock(label="a.py", content="x = 1", language="py")
    prompt = build_prompt("Warum?", [block], DECISION)

    assert prompt.index("# Kontext") < prompt.index("# Frage")
    assert prompt.rstrip().endswith("Warum?")
    assert "a.py" in prompt and "x = 1" in prompt


def test_empty_blocks_are_dropped():
    blocks = [ContextBlock(label="leer", content="   "),
              ContextBlock(label="voll", content="Inhalt")]
    prompt = build_prompt("Frage", blocks, DECISION)

    assert "voll" in prompt and "leer" not in prompt


def test_oversized_context_is_truncated_visibly():
    huge = ContextBlock(label="gross.txt", content="a" * 500_000)
    prompt = build_prompt("Frage", [huge], DECISION)

    assert len(prompt) < DECISION.max_context_chars + 2000
    assert "Zeichen gekuerzt" in prompt, "truncation must be visible to the reader"


def test_budget_is_shared_between_blocks():
    blocks = [ContextBlock(label=f"f{i}", content="a" * 100_000) for i in range(4)]
    prompt = build_prompt("Frage", blocks, DECISION)

    assert len(prompt) < DECISION.max_context_chars + 4000
    for i in range(4):
        assert f"f{i}" in prompt, "every block must survive, shortened"


def test_ranking_prompt_anonymises_and_maps_back():
    prompt, label_to_model = build_ranking_prompt("Frage", STAGE1, DECISION)

    assert label_to_model == {"Response A": "m1", "Response B": "m2"}
    assert "m1" not in prompt and "m2" not in prompt, "evaluators must not see names"
    assert "Response A:" in prompt and "Response B:" in prompt


def test_ranking_prompt_carries_the_profile_rubric():
    decision_prompt, _ = build_ranking_prompt("Frage", STAGE1, DECISION)
    research_prompt, _ = build_ranking_prompt("Frage", STAGE1, get_profile("research"))

    assert "Trade-off honesty" in decision_prompt
    assert "Coverage" in research_prompt
    assert "Trade-off honesty" not in research_prompt


def test_ranking_prompt_keeps_the_parseable_format_instruction():
    # parse_ranking_from_text() depends on this exact header.
    prompt, _ = build_ranking_prompt("Frage", STAGE1, DECISION)
    assert "FINAL RANKING:" in prompt


def test_chairman_prompt_carries_the_profile_output_schema():
    stage2 = [{"model": "m1", "ranking": "FINAL RANKING:\n1. Response A"}]
    prompt = build_chairman_prompt("Frage", STAGE1, stage2, DECISION)

    assert "## Dissens im Konzil" in prompt
    assert "## Empfehlung" in prompt
    assert "STAGE 2" in prompt


def test_chairman_prompt_omits_stage2_when_there_was_none():
    prompt = build_chairman_prompt("Frage", STAGE1, [], QUICK)

    assert "STAGE 2" not in prompt
    assert "Peer Rankings" not in prompt
    assert "## Kurzfassung" in prompt


def test_every_profile_has_a_usable_output_schema():
    for name, profile in PROFILES.items():
        prompt = build_chairman_prompt("Frage", STAGE1, [], profile)
        assert profile.output_schema in prompt, name
        assert "##" in profile.output_schema, f"{name} schema needs headings"
