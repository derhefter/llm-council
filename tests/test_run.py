"""The full council run: stages, degradation, stats, persistence."""

import asyncio

from backend import storage
from backend.context import ContextBlock
from backend.council import run_full_council
from backend.profiles import get_profile

DECISION = get_profile("decision")
QUICK = get_profile("quick")


def run(*args, **kwargs):
    return asyncio.run(run_full_council(*args, **kwargs))


def test_decision_profile_runs_all_three_stages(stub_models):
    stage1, stage2, stage3, meta = run("Frage", profile=DECISION)

    assert len(stage1) == len(DECISION.models)
    assert len(stage2) == len(DECISION.models)
    assert stage3["model"] == DECISION.chairman
    assert len(meta["aggregate_rankings"]) == len(DECISION.models)
    assert meta["profile"] == "decision"


def test_quick_profile_skips_peer_review(stub_models):
    stage1, stage2, stage3, meta = run("Frage", profile=QUICK)

    assert len(stage1) == 2
    assert stage2 == []
    assert meta["aggregate_rankings"] == []
    assert meta["label_to_model"] == {}
    assert stage3["response"], "the chairman still answers"


def test_context_reaches_the_chairman(stub_models):
    blocks = [ContextBlock(label="notiz.md", content="Wichtiger Hinweis")]
    _, _, stage3, meta = run("Frage", profile=QUICK, context_blocks=blocks)

    assert "kontext=True" in stage3["response"]
    assert meta["context_labels"] == ["notiz.md"]


def test_one_failing_model_does_not_stop_the_run(stub_models):
    stub_models(failing_models={DECISION.models[0]})
    stage1, stage2, stage3, meta = run("Frage", profile=DECISION)

    assert len(stage1) == len(DECISION.models) - 1
    assert DECISION.models[0] not in [r["model"] for r in stage1]
    assert stage3["response"], "the council still concludes"
    assert meta["run_stats"]["failed_calls"] >= 1


def test_all_models_failing_returns_an_explicit_error(stub_models):
    stub_models(failing_models=set(DECISION.models))
    stage1, stage2, stage3, meta = run("Frage", profile=DECISION)

    assert stage1 == [] and stage2 == []
    assert stage3["model"] == "error"
    assert "failed" in stage3["response"].lower()


def test_a_failing_chairman_is_reported_not_hidden(stub_models):
    stub_models(chairman_fails=True)
    stage1, _, stage3, _ = run("Frage", profile=QUICK)

    assert stage1, "stage 1 succeeded"
    assert "Error" in stage3["response"]


def test_run_stats_add_up_across_stages(stub_models):
    _, _, _, meta = run("Frage", profile=DECISION)
    stats = meta["run_stats"]

    calls = len(DECISION.models) * 2 + 1  # stage1 + stage2 + chairman
    assert stats["prompt_tokens"] == 100 * calls
    assert stats["completion_tokens"] == 50 * calls
    assert round(stats["cost_usd"], 4) == round(0.001 * calls, 4)
    assert stats["failed_calls"] == 0
    assert set(stats["stages"]) == {"stage1", "stage2", "stage3"}


def test_metadata_survives_a_save_and_reload(stub_models, store):
    stage1, stage2, stage3, meta = run("Frage", profile=DECISION)

    storage.create_conversation("abc")
    storage.add_user_message("abc", "Frage")
    storage.add_assistant_message("abc", stage1, stage2, stage3, meta)

    reloaded = storage.get_conversation("abc")["messages"][-1]
    assert reloaded["metadata"]["aggregate_rankings"] == meta["aggregate_rankings"]
    assert reloaded["metadata"]["profile"] == "decision"
    assert reloaded["metadata"]["run_stats"]["cost_usd"] == meta["run_stats"]["cost_usd"]


def test_a_pre_metadata_conversation_still_loads(store):
    """Files written before metadata existed must not break on read."""
    storage.create_conversation("alt")
    conversation = storage.get_conversation("alt")
    conversation["messages"].append(
        {"role": "assistant", "stage1": [], "stage2": [], "stage3": {}}
    )
    storage.save_conversation(conversation)

    message = storage.get_conversation("alt")["messages"][-1]
    assert message.get("metadata", {}) == {}
