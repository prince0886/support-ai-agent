"""API integration tests: seeded data, workflow, persistence and metrics."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app

NEW_TICKET = {
    "message": (
        "Hi, my order NW-77120 was supposed to arrive on Monday and the tracking has not updated in six days. "
        "We need the tent for a trip this weekend. Can you check what is happening?"
    ),
    "customer_name": "Riley Cooper",
    "customer_email": "riley.cooper@example.com",
}


def test_health_and_seeded_inbox(client):
    health = client.get("/api/health").json()
    assert health["status"] == "ok"

    response = client.get("/api/tickets")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 9
    assert len(payload["items"]) == 9
    assert payload["facets"]["status"] == {"new": 5, "in_progress": 1, "escalated": 1, "resolved": 2}

    references = {item["reference"] for item in payload["items"]}
    assert "SP-1001" in references and "SP-1009" in references


def test_demo_scenarios_are_classified(client):
    items = client.get("/api/tickets").json()["items"]
    by_name = {item["customer_name"]: item for item in items}

    assert by_name["Maya Chen"]["category"] == "shipping"
    assert by_name["Maya Chen"]["priority"] == "high"
    assert by_name["Maya Chen"]["requires_human"] is False
    assert by_name["Priya Raman"]["requires_human"] is True
    assert by_name["Angela Torres"]["status"] == "escalated"
    assert by_name["Tom Becker"]["priority"] == "urgent"


def test_metrics_are_derived_from_tickets(client):
    metrics = client.get("/api/metrics").json()
    tickets = client.get("/api/tickets").json()["items"]
    totals = metrics["totals"]

    assert totals["total"] == len(tickets) == 9
    assert totals["open"] == totals["new"] + totals["in_progress"] + totals["escalated"]
    assert totals["awaiting_review"] == sum(1 for item in tickets if item["requires_human"] and item["status"] != "resolved")
    assert sum(metrics["by_category"].values()) == 9
    assert sum(metrics["by_priority"].values()) == 9
    assert sum(metrics["by_status"].values()) == 9
    assert metrics["by_status"] == {
        "new": 5,
        "in_progress": 1,
        "escalated": 1,
        "resolved": 2,
    }
    assert len(metrics["trend"]) == 7
    assert metrics["recent"][0]["created_at"] >= metrics["recent"][-1]["created_at"]


def test_filters_and_search(client):
    new_only = client.get("/api/tickets", params={"status": "new"}).json()
    assert new_only["total"] == 5
    assert all(item["status"] == "new" for item in new_only["items"])

    refunds = client.get("/api/tickets", params={"category": "refund"}).json()
    assert refunds["total"] == 2
    assert all(item["category"] == "refund" for item in refunds["items"])

    urgent = client.get("/api/tickets", params={"priority": "urgent"}).json()
    assert urgent["total"] >= 1

    found = client.get("/api/tickets", params={"q": "priya.raman"}).json()
    assert found["total"] == 1
    assert found["items"][0]["customer_name"] == "Priya Raman"

    review = client.get("/api/tickets", params={"requires_human": True}).json()
    assert review["total"] >= 4


def test_validation_errors(client):
    assert client.get("/api/tickets", params={"category": "nonsense"}).status_code == 422
    assert client.get("/api/tickets", params={"status": "closed"}).status_code == 422
    assert client.get("/api/tickets/99999").status_code == 404
    assert client.post("/api/tickets", json={"message": "  "}).status_code == 422


def test_full_human_workflow(client):
    created = client.post("/api/tickets", json=NEW_TICKET)
    assert created.status_code == 201
    ticket = created.json()
    ticket_id = ticket["id"]

    assert ticket["status"] == "new"
    assert ticket["category"] == "shipping"
    assert ticket["requires_human"] is False
    assert ticket["draft_reply"]
    assert ticket["sources"]
    assert ticket["sources"][0]["slug"] == "shipping-delays"
    assert ticket["messages"][0]["role"] == "customer"
    assert ticket["ai_mode"] == "fallback"

    edited = client.post(f"/api/tickets/{ticket_id}/draft", json={"body": "Edited, human-reviewed reply."})
    assert edited.status_code == 200
    assert edited.json()["draft_status"] == "edited"
    assert edited.json()["draft_reply"] == "Edited, human-reviewed reply."

    approved = client.post(f"/api/tickets/{ticket_id}/approve", json={"body": None})
    assert approved.status_code == 200
    approved_payload = approved.json()
    assert approved_payload["draft_status"] == "approved"
    assert approved_payload["approved_reply"] == "Edited, human-reviewed reply."
    assert approved_payload["status"] == "in_progress"
    assert any(message["role"] == "assistant" for message in approved_payload["messages"])

    resolved = client.post(f"/api/tickets/{ticket_id}/resolve", json={"note": "Refund not needed."})
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "resolved"
    assert resolved.json()["resolved_at"] is not None

    # Metrics update from live data after the human actions.
    metrics = client.get("/api/metrics").json()
    assert metrics["totals"]["resolved"] == 3
    assert metrics["by_status"]["in_progress"] == 1  # the seeded technical ticket


def test_blank_approval_body_falls_back_to_the_stored_draft(client):
    """A whitespace-only body is normalised to None, so the existing draft is used."""
    response = client.post(
        "/api/tickets",
        json={"message": "Do you have a physical store in Berlin that I can visit this week?", "customer_name": "No Store"},
    )
    assert response.status_code == 201
    ticket_id = response.json()["id"]
    original_draft = response.json()["draft_reply"]

    approved = client.post(f"/api/tickets/{ticket_id}/approve", json={"body": "   "})
    assert approved.status_code == 200
    payload = approved.json()
    assert payload["approved_reply"] == original_draft
    assert payload["draft_status"] == "approved"


def test_escalate_and_reopen(client):
    created = client.post("/api/tickets", json=NEW_TICKET).json()
    ticket_id = created["id"]

    escalated = client.post(
        f"/api/tickets/{ticket_id}/escalate",
        json={"reason": "Customer is asking for a delivery guarantee we cannot make."},
    )
    assert escalated.status_code == 200
    payload = escalated.json()
    assert payload["status"] == "escalated"
    assert payload["requires_human"] is True
    assert "delivery guarantee" in payload["escalation_reason"]
    assert any(event["action"] == "escalated" for event in payload["events"])

    reopened = client.post(f"/api/tickets/{ticket_id}/reopen", json={"note": "Following up with the carrier."})
    assert reopened.status_code == 200
    assert reopened.json()["status"] == "in_progress"
    assert reopened.json()["resolved_at"] is None


def test_internal_note_does_not_change_status(client):
    created = client.post("/api/tickets", json=NEW_TICKET).json()
    response = client.post(
        f"/api/tickets/{created['id']}/messages",
        json={"body": "Checking with the fulfilment team.", "internal": True},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "new"
    note = payload["messages"][-1]
    assert note["is_internal"] is True
    assert note["role"] == "note"


def test_knowledge_endpoints(client):
    listing = client.get("/api/knowledge").json()
    assert listing["total"] == 20
    assert sum(listing["by_category"].values()) == 20
    assert all(len(article["content"]) > 100 for article in listing["items"])

    article = client.get("/api/knowledge/refund-policy").json()
    assert article["title"] == "30-day refund policy"

    search = client.post("/api/knowledge/search", json={"query": "refund window", "top_k": 2}).json()
    assert search["hits"][0]["slug"] == "refund-exceptions"
    assert search["hits"][0]["score"] == 1.0

    assert client.get("/api/knowledge/does-not-exist").status_code == 404


def test_demo_reset_restores_the_seed(client):
    client.post("/api/tickets", json=NEW_TICKET)
    assert client.get("/api/tickets").json()["total"] == 10

    reset = client.post("/api/system/demo/reset")
    assert reset.status_code == 200
    assert reset.json()["tickets"] == 9
    assert client.get("/api/tickets").json()["total"] == 9


def test_tickets_persist_across_app_restarts(tmp_path):
    database_file = tmp_path / "persist.db"
    settings = Settings(
        database_url=f"sqlite:///{database_file.as_posix()}",
        llm_enabled=False,
        seed_on_startup=True,
    )

    with TestClient(create_app(settings)) as first:
        created = first.post("/api/tickets", json=NEW_TICKET).json()
        ticket_id = created["id"]

    with TestClient(create_app(settings)) as second:
        reloaded = second.get(f"/api/tickets/{ticket_id}")
        assert reloaded.status_code == 200
        assert reloaded.json()["reference"] == created["reference"]
        assert second.get("/api/tickets").json()["total"] == 10