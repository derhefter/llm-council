"""The MCP tools other repositories call."""

import asyncio

import pytest

from backend import mcp_server
from backend.profiles import DEFAULT_PROFILE


@pytest.fixture(autouse=True)
def clean_runs():
    mcp_server._RUNS.clear()
    yield
    mcp_server._RUNS.clear()


async def finish(run_id):
    """Poll like a client would, until the run leaves 'running'."""
    for _ in range(200):
        result = await mcp_server.council_result(run_id)
        if result["status"] != "running":
            return result
        await asyncio.sleep(0.01)
    raise AssertionError("run never finished")


def test_profiles_are_listed_with_cost_expectations():
    profiles = mcp_server.council_profiles()

    assert {p["name"] for p in profiles} == {"quick", "decision", "research"}
    default = [p for p in profiles if p["default"]]
    assert len(default) == 1 and default[0]["name"] == DEFAULT_PROFILE
    assert all(p["expected_calls"] > 0 and p["expected_latency"] for p in profiles)


def test_start_returns_immediately_then_result_completes(stub_models, store):
    async def scenario():
        started = await mcp_server.council_start("Frage", profile="decision")
        assert started["status"] == "running"
        assert started["run_id"]
        return await finish(started["run_id"])

    result = asyncio.run(scenario())

    assert result["status"] == "complete"
    assert len(result["responders"]) == 4
    assert len(result["aggregate_ranking"]) == 4
    assert result["run_stats"]["cost_usd"] > 0
    assert result["conversation_id"]


def test_context_and_files_reach_the_council(tmp_path, stub_models, store):
    note = tmp_path / "notiz.md"
    note.write_text("Hinweis", encoding="utf-8")

    async def scenario():
        started = await mcp_server.council_start(
            "Frage", profile="quick", context="Randbedingung", files=[str(note)]
        )
        return await finish(started["run_id"])

    result = asyncio.run(scenario())

    assert "kontext=True" in result["answer"]
    assert set(result["context_labels"]) == {"context", str(note)}


def test_an_unreadable_file_is_reported_not_fatal(stub_models, store):
    async def scenario():
        started = await mcp_server.council_start(
            "Frage", profile="quick", files=["/gibt/es/nicht.md"]
        )
        return await finish(started["run_id"])

    assert asyncio.run(scenario())["status"] == "complete"


def test_council_ask_is_blocking_and_quick(stub_models, store):
    result = asyncio.run(mcp_server.council_ask("Frage"))

    assert result["status"] == "complete"
    assert result["profile"] == "quick"
    assert len(result["responders"]) == 2
    assert result["aggregate_ranking"] == []


def test_total_failure_is_reported_as_failed(stub_models, store):
    from backend.profiles import get_profile
    stub_models(failing_models=set(get_profile("quick").models))

    result = asyncio.run(mcp_server.council_ask("Frage"))
    assert result["status"] == "failed"
    assert result["error"]


def test_an_unknown_run_id_does_not_raise():
    result = asyncio.run(mcp_server.council_result("gibtsnicht"))
    assert result["status"] == "unknown"


def test_an_unknown_profile_is_rejected_early(stub_models, store):
    with pytest.raises(ValueError, match="Unknown profile"):
        asyncio.run(mcp_server.council_start("Frage", profile="gibtsnicht"))


def test_write_adr_after_a_finished_run(tmp_path, stub_models, store):
    async def scenario():
        started = await mcp_server.council_start("Frage", profile="quick")
        await finish(started["run_id"])
        return started["run_id"]

    run_id = asyncio.run(scenario())
    written = mcp_server.council_write_adr(run_id, adr_dir=str(tmp_path / "adrs"))

    assert "path" in written
    assert "## Empfehlung" in open(written["path"], encoding="utf-8").read()


def test_write_adr_refuses_an_unknown_run():
    assert "error" in mcp_server.council_write_adr("gibtsnicht")
