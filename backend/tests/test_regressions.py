"""Regression tests for the QA audit findings (BUG-001..BUG-003, BUG-007)."""

from __future__ import annotations

NEW_TICKET = {
    "message": (
        "Hi, my order NW-51550 arrived with a cracked lid and I would like to know what to do next."
    ),
    "customer_name": "Regression Tester",
    "customer_email": "regression@example.com",
}


def _new_ticket(client) -> dict:
    response = client.post("/api/tickets", json=NEW_TICKET)
    assert response.status_code == 201
    return response.json()


def test_bug_001_cannot_approve_a_resolved_ticket(client):
    """A closed ticket must reject approval until it is reopened."""
    created = _new_ticket(client)
    ticket_id = created["id"]

    resolved = client.post(f"/api/tickets/{ticket_id}/resolve", json={})
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "resolved"
    before = resolved.json()
    approved_before = before["approved_reply"]
    messages_before = len(before["messages"])
    events_before = len(before["events"])

    response = client.post(
        f"/api/tickets/{ticket_id}/approve",
        json={"body": "This should never be accepted."},
    )
    assert response.status_code == 409, response.text
    assert "reopen" in response.json()["detail"].lower()

    # Nothing on the closed ticket may change.
    after = client.get(f"/api/tickets/{ticket_id}").json()
    assert after["status"] == "resolved"
    assert after["approved_reply"] == approved_before
    assert len(after["messages"]) == messages_before
    assert len(after["events"]) == events_before
    assert "This should never be accepted." not in {m["body"] for m in after["messages"]}

    # Reopening restores the ability to approve.
    assert client.post(f"/api/tickets/{ticket_id}/reopen", json={}).status_code == 200
    reopened = client.post(f"/api/tickets/{ticket_id}/approve", json={"body": "Now allowed."})
    assert reopened.status_code == 200
    assert reopened.json()["approved_reply"] == "Now allowed."


def test_bug_001_cannot_edit_a_draft_on_a_resolved_ticket(client):
    created = _new_ticket(client)
    ticket_id = created["id"]
    client.post(f"/api/tickets/{ticket_id}/resolve", json={})

    response = client.post(f"/api/tickets/{ticket_id}/draft", json={"body": "Changed after closing."})
    assert response.status_code == 409
    assert "reopen" in response.json()["detail"].lower()


def test_bug_002_resolve_with_body_and_note_creates_one_note(client):
    """The most common closing pattern must not duplicate the internal note."""
    created = _new_ticket(client)
    ticket_id = created["id"]

    response = client.post(
        f"/api/tickets/{ticket_id}/resolve",
        json={
            "body": "Final reply to the customer about the cracked lid.",
            "note": "Internal note: defect case opened with the carrier.",
        },
    )
    assert response.status_code == 200
    payload = response.json()

    notes = [message for message in payload["messages"] if message["is_internal"]]
    assert len(notes) == 1, f"expected 1 internal note, got {len(notes)}"
    assert notes[0]["body"] == "Internal note: defect case opened with the carrier."
    assert notes[0]["role"] == "note"

    replies = [m for m in payload["messages"] if m["role"] == "assistant"]
    assert len(replies) == 1
    assert replies[0]["body"] == "Final reply to the customer about the cracked lid."
    assert payload["status"] == "resolved"

    # Persisted, not just in the response.
    stored = client.get(f"/api/tickets/{ticket_id}").json()
    assert len([m for m in stored["messages"] if m["is_internal"]]) == 1


def test_bug_002_resolve_with_note_only_creates_one_note(client):
    created = _new_ticket(client)
    ticket_id = created["id"]

    response = client.post(
        f"/api/tickets/{ticket_id}/resolve",
        json={"note": "Closed after email confirmation."},
    )
    assert response.status_code == 200
    payload = response.json()
    assert len([m for m in payload["messages"] if m["is_internal"]]) == 1


def test_bug_003_knowledge_total_respects_category_filter(client):
    response = client.get("/api/knowledge", params={"category": "billing"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == len(payload["items"]) == 4
    assert all(article["category"] == "billing" for article in payload["items"])

    # The pills still describe the whole corpus.
    assert sum(payload["by_category"].values()) == 20

    everything = client.get("/api/knowledge").json()
    assert everything["total"] == len(everything["items"]) == 20


def test_bug_003_knowledge_total_respects_search_filter(client):
    payload = client.get("/api/knowledge", params={"q": "refund"}).json()
    assert payload["total"] == len(payload["items"])
    assert 0 < payload["total"] < 20

    empty = client.get("/api/knowledge", params={"q": "zzzz-no-such-article"}).json()
    assert empty["total"] == 0
    assert empty["items"] == []


def test_bug_007_approve_and_resolve_strip_whitespace(client):
    created = _new_ticket(client)
    ticket_id = created["id"]

    # Whitespace-only body is normalised to None, so the draft is approved
    # instead of persisting a blank reply.
    response = client.post(f"/api/tickets/{ticket_id}/approve", json={"body": "   ", "note": "  "})
    assert response.status_code == 200
    payload = response.json()
    assert payload["approved_reply"].strip() != ""
    assert all(not m["is_internal"] or m["body"].strip() for m in payload["messages"])
