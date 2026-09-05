"""The web API keeps working, and now persists what it used to drop."""

import json

import pytest
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture
def client(stub_models, store):
    return TestClient(app)


def test_health_and_profiles(client):
    assert client.get("/").json()["status"] == "ok"

    profiles = client.get("/api/profiles").json()
    assert {p["name"] for p in profiles} == {"quick", "decision", "research"}
    assert all("expected_calls" in p for p in profiles)


def test_message_returns_all_stages_and_metadata(client):
    cid = client.post("/api/conversations", json={}).json()["id"]
    body = client.post(f"/api/conversations/{cid}/message",
                       json={"content": "Frage"}).json()

    assert len(body["stage1"]) == 4 and len(body["stage2"]) == 4
    assert body["metadata"]["profile"] == "decision"
    assert body["metadata"]["aggregate_rankings"]


def test_metadata_survives_reopening_a_conversation(client):
    cid = client.post("/api/conversations", json={}).json()["id"]
    client.post(f"/api/conversations/{cid}/message", json={"content": "Frage"})

    message = client.get(f"/api/conversations/{cid}").json()["messages"][-1]
    assert message["metadata"]["aggregate_rankings"], \
        "rankings used to vanish on reload"


def test_conversation_gets_a_generated_title(client):
    cid = client.post("/api/conversations", json={}).json()["id"]
    client.post(f"/api/conversations/{cid}/message", json={"content": "Frage"})

    assert client.get(f"/api/conversations/{cid}").json()["title"] == "Ein kurzer Titel"


def test_missing_conversation_is_404(client):
    assert client.get("/api/conversations/gibtsnicht").status_code == 404
    assert client.post("/api/conversations/gibtsnicht/message",
                       json={"content": "x"}).status_code == 404


def stream_events(client, cid, payload):
    with client.stream("POST", f"/api/conversations/{cid}/message/stream",
                       json=payload) as response:
        return [json.loads(line[6:]) for line in response.iter_lines()
                if line.startswith("data: ")]


def test_stream_emits_the_full_stage_sequence(client):
    cid = client.post("/api/conversations", json={}).json()["id"]
    events = stream_events(client, cid, {"content": "Frage"})
    types = [e["type"] for e in events]

    assert types == ["stage1_start", "stage1_complete", "stage2_start",
                     "stage2_complete", "stage3_start", "stage3_complete",
                     "title_complete", "complete"]


def test_stream_honours_a_profile_without_peer_review(client):
    cid = client.post("/api/conversations", json={}).json()["id"]
    types = [e["type"] for e in stream_events(client, cid,
                                              {"content": "Frage", "profile": "quick"})]

    assert "stage2_skipped" in types
    assert "stage2_start" not in types

    stored = client.get(f"/api/conversations/{cid}").json()["messages"][-1]
    assert len(stored["stage1"]) == 2
    assert stored["metadata"]["profile"] == "quick"


def test_stream_persists_metadata_too(client):
    cid = client.post("/api/conversations", json={}).json()["id"]
    stream_events(client, cid, {"content": "Frage"})

    stored = client.get(f"/api/conversations/{cid}").json()["messages"][-1]
    assert stored["metadata"]["aggregate_rankings"]
