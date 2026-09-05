"""The CLI surface: exit codes, report shape, ADR export."""

import json

import pytest

from backend import storage
from backend.cli import main
from backend.config import MissingAPIKeyError
from backend.openrouter import OpenRouterAuthError


def test_profiles_needs_no_api_call(capsys):
    assert main(["profiles"]) == 0

    out = capsys.readouterr().out
    for name in ("quick", "decision", "research"):
        assert name in out
    assert "(default)" in out


def test_log_on_an_empty_store(capsys, store):
    assert main(["log"]) == 0
    assert "Noch keine Runs" in capsys.readouterr().out


def test_ask_prints_answer_ranking_and_stats(capsys, stub_models, store):
    assert main(["ask", "Frage", "--profile", "decision", "--quiet"]) == 0

    out = capsys.readouterr().out
    assert "## Empfehlung" in out
    assert "Peer-Ranking" in out
    assert "Profil `decision`" in out
    assert "$" in out and "Tokens" in out


def test_quick_run_reports_no_ranking(capsys, stub_models, store):
    assert main(["ask", "Frage", "--profile", "quick", "--quiet"]) == 0

    out = capsys.readouterr().out
    assert "Peer-Ranking" not in out
    assert "Profil `quick` · 2 Antworten" in out


def test_json_output_is_machine_readable(capsys, stub_models, store):
    assert main(["ask", "Frage", "--profile", "quick", "--json", "--quiet"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["question"] == "Frage"
    assert payload["metadata"]["profile"] == "quick"
    assert payload["metadata"]["conversation_id"]
    assert len(payload["stage1"]) == 2


def test_file_context_is_passed_through(tmp_path, capsys, stub_models, store):
    note = tmp_path / "notiz.md"
    note.write_text("Wichtiger Hinweis", encoding="utf-8")

    assert main(["ask", "Frage", "--profile", "quick", "--file", str(note),
                 "--no-repo-info", "--quiet"]) == 0

    assert "kontext=True" in capsys.readouterr().out


def test_an_unreadable_file_warns_but_does_not_abort(capsys, stub_models, store):
    assert main(["ask", "Frage", "--profile", "quick",
                 "--file", "/gibt/es/nicht.md", "--quiet"]) == 0

    captured = capsys.readouterr()
    assert "warn: cannot read" in captured.err
    assert "## Empfehlung" in captured.out


def test_out_writes_a_file_instead_of_stdout(tmp_path, capsys, stub_models, store):
    target = tmp_path / "antwort.md"
    assert main(["ask", "Frage", "--profile", "quick", "--out", str(target),
                 "--quiet"]) == 0

    assert "## Empfehlung" in target.read_text(encoding="utf-8")
    assert capsys.readouterr().out.strip() == ""


def test_adr_is_written_and_numbered(tmp_path, stub_models, store):
    adr_dir = tmp_path / "decisions"
    for _ in range(2):
        assert main(["ask", "Frage", "--profile", "quick", "--adr",
                     "--adr-dir", str(adr_dir), "--quiet"]) == 0

    written = sorted(p.name for p in adr_dir.glob("*.md"))
    assert len(written) == 2
    assert written[0].startswith("0001-") and written[1].startswith("0002-")


def test_the_run_is_persisted_and_listed(capsys, stub_models, store):
    main(["ask", "Frage", "--profile", "quick", "--quiet"])
    capsys.readouterr()

    main(["log"])
    assert "Ein kurzer Titel" in capsys.readouterr().out

    saved = storage.list_conversations()
    assert len(saved) == 1


def test_total_model_failure_exits_nonzero(capsys, stub_models, store):
    from backend.profiles import get_profile
    stub_models(failing_models=set(get_profile("quick").models))

    assert main(["ask", "Frage", "--profile", "quick", "--quiet"]) == 1
    assert "Alle Modelle sind ausgefallen" in capsys.readouterr().err


@pytest.mark.parametrize("error", [
    MissingAPIKeyError("kein Schluessel"),
    OpenRouterAuthError("Schluessel abgelehnt"),
])
def test_credential_problems_exit_with_code_2(error, monkeypatch, capsys, store):
    """A key problem must be loud - it used to look like 'all models failed'."""
    async def boom(*a, **k):
        raise error

    monkeypatch.setattr("backend.cli.run_full_council", boom)

    assert main(["ask", "Frage", "--profile", "quick"]) == 2
    assert "error:" in capsys.readouterr().err


def test_unknown_profile_is_rejected_by_the_parser():
    with pytest.raises(SystemExit):
        main(["ask", "Frage", "--profile", "gibtsnicht"])
