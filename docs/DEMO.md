# Demo script

A 3-minute walkthrough for judges. Everything below runs on the seeded demo data.

## Before you start

```bash
cd backend && uvicorn app.main:app --port 8000
cd frontend && npm run dev
```

Open <http://localhost:5173>. Click **Reset demo data** in Settings if a previous run left the queue messy.

---

## 0:00 — Overview (20s)

Point at the four metric cards and say: *these are computed from the ticket rows on every request, not hardcoded.*

- **Total tickets 9**, **Open 7**, **Needs a human 4**, **Resolved 2**
- Ticket volume chart: received vs resolved over 7 days
- AI performance: 86% average confidence, 44% human-review rate
- Right column: the review queue, urgent first

Say: *SupportPilot clears routine work and deliberately keeps the risky work for a person.*

---

## 0:20 — Submit a live query (40s)

Click **New ticket** → click the **Policy exception** chip (Angela Torres) → **Analyze & create ticket**.

Watch the pipeline complete in one request. The ticket opens with:

- **Shipping… no, Refund** · **High** · **Angry**
- **Escalation triggers:** Policy exception · Financial decision · Sensitive complaint
- **Recommended action: Needs human review**
- Confidence ring

Read the escalation reason aloud: *only a supervisor can approve an exception.*

Say: *the customer asked for something outside policy, and the app refused to decide it.*

---

## 1:00 — Show the grounding (40s)

Scroll to **Knowledge used**. Point at:

- the retrieved article (top match, score bar)
- the quoted excerpt, which is exactly what the draft is based on

Say: *the reply can only use what is quoted here. That is why it cannot invent a refund approval.*

Scroll to the draft. Note the amber **AI draft — not sent** banner and the "Drafted by" engine badge.

---

## 1:40 — The routine path (40s)

Go to **Support Inbox**, open **Maya Chen — delayed shipment**.

- **Shipping · High · Routine**, no escalation triggers
- Draft cites the delay policy and asks for the order number instead of promising a date
- Edit one line, click **Save draft** → badge changes to **Edited by human**
- Click **Approve & send** → green **Human-approved reply** panel appears, status becomes **In progress**
- The conversation history now shows the approved reply

Say: *AI did the work; a human signed off. That separation is the product.*

---

## 2:20 — Escalate one (20s)

Open **Priya Raman — failed payment**.

- Escalated automatically: *Financial decision*
- Click **Escalate**, type a reason, confirm → status **Escalated**, event added to Activity

---

## 2:40 — Prove it persists (20s)

Back to **Overview**: the numbers moved. Resolved and open counts reflect the actions you just took.

Hard-refresh the browser (F5). The tickets, the approved reply and the escalation are all still there.

Optionally open Settings → **Test connection** to show the live AI status, including the honest fallback state.

---

## Talking points if asked

**Why is it in fallback mode?** No valid model credential was available in this environment. The app reports
this from the server and falls back to a deterministic analyst, so the whole workflow still runs. Add a key to
`.env` and the same pipeline uses the model.

**How do you stop hallucinated policy?** Three layers: retrieval-only context, an explicit no-knowledge rule that
escalates instead of answering, and a post-generation guardrail that discards drafts containing commitments.

**What is not built?** No email sending, no order/payment lookup, no auth. All listed in Settings → Limitations
and in the README.

**What would production need?** Postgres, auth and roles, a job queue, read-only order/payment tools, a real
helpdesk integration, and embedding-based retrieval.
