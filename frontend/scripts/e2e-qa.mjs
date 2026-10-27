// End-to-end UI test against the real app.
//
// Prerequisite: build the frontend and run the API so that http://127.0.0.1:8000
// serves the built dashboard, e.g.
//   npm run build && cd ../backend && uvicorn app.main:app --port 8000
// Then run: npm run test:e2e
//
// It resets nothing itself; run Settings -> Reset demo data first if the queue
// has drifted from the seeded 9 tickets. Set CHROME_PATH to override the browser.
import puppeteer from "puppeteer-core";
import fs from "node:fs";

const BASE = process.env.E2E_BASE_URL ?? "http://127.0.0.1:8000";
const CHROME =
  process.env.CHROME_PATH ?? "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const OUT = process.env.E2E_OUT_DIR ?? "e2e-output";
fs.mkdirSync(OUT, { recursive: true });

const results = [];
const consoleErrors = [];
const pageErrors = [];
const failedRequests = [];

function check(name, ok, detail = "") {
  results.push({ name, ok, detail });
  console.log(`${ok ? "PASS" : "FAIL"}  ${name}${detail ? ` — ${detail}` : ""}`);
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// Preflight: fail with a clear message instead of a raw connection error.
async function waitForApi(timeoutMs = 30000) {
  const deadline = Date.now() + timeoutMs;
  let lastError = "no response";
  while (Date.now() < deadline) {
    try {
      const response = await fetch(`${BASE}/api/health`, { signal: AbortSignal.timeout(4000) });
      if (response.ok) return true;
      lastError = `HTTP ${response.status}`;
    } catch (error) {
      lastError = error.message;
    }
    await sleep(700);
  }
  throw new Error(
    `Backend not reachable at ${BASE} (${lastError}).\n` +
      "Start it with: powershell -ExecutionPolicy Bypass -File scripts/start-backend.ps1",
  );
}

async function waitForText(page, text, timeout = 12000) {
  const start = Date.now();
  while (Date.now() - start < timeout) {
    const found = await page.evaluate(
      (t) => document.body.innerText.toLowerCase().includes(t.toLowerCase()),
      text,
    );
    if (found) return true;
    await sleep(150);
  }
  return false;
}

async function clickByText(page, selector, text, { exact = false, scope = null } = {}) {
  const handle = await page.evaluateHandle(
    (sel, txt, isExact, scopeSel) => {
      const root = scopeSel ? document.querySelector(scopeSel) : document;
      if (!root) return null;
      const nodes = Array.from(root.querySelectorAll(sel));
      const normalize = (value) => value.replace(/\s+/g, " ").trim().toLowerCase();
      const target = normalize(txt);
      return (
        nodes.find((n) => (isExact ? normalize(n.innerText) === target : normalize(n.innerText).includes(target))) ||
        null
      );
    },
    selector,
    text,
    exact,
    scope,
  );
  const element = handle.asElement();
  if (!element) throw new Error(`No ${selector} containing "${text}"`);
  await element.click();
  return true;
}

const browser = await puppeteer.launch({
  executablePath: CHROME,
  headless: "new",
  args: ["--no-sandbox", "--disable-gpu", "--window-size=1440,1000"],
  defaultViewport: { width: 1440, height: 1000 },
});

const page = await browser.newPage();
page.on("console", (msg) => {
  if (msg.type() === "error") consoleErrors.push(msg.text());
});
page.on("pageerror", (err) => pageErrors.push(err.message));
page.on("requestfailed", (req) => failedRequests.push(`${req.method()} ${req.url()} ${req.failure()?.errorText}`));

try {
  await waitForApi();

  // ---- 1. Overview loads with live metrics -------------------------------
  await page.goto(`${BASE}/`, { waitUntil: "networkidle2", timeout: 30000 });
  await waitForText(page, "Total tickets");
  const overviewText = await page.evaluate(() => document.body.innerText);
  check("Overview renders metrics", /Total tickets/i.test(overviewText));
  const initialTotal = Number(
    (overviewText.match(/TOTAL TICKETS\s*\n?\s*(\d+)/i) || [])[1] ?? -1,
  );
  check(
    "Total tickets read from API",
    initialTotal === 9,
    `got ${initialTotal}${initialTotal === 9 ? "" : " (run Settings → Reset demo data first)"}`,
  );
  check("Sidebar shows honest engine state", /Deterministic analyst|Fallback/i.test(overviewText));
  await page.screenshot({ path: `${OUT}/01-overview.png` });

  // ---- 2. Submit a new ticket through the modal -------------------------
  await clickByText(page, "button", "New ticket");
  await waitForText(page, "New customer query");
  await clickByText(page, "button", "Policy exception");
  await sleep(300);
  const draftMessage = await page.$eval("#ticket-message", (el) => el.value);
  check("Demo scenario fills the message", draftMessage.length > 100);
  await page.screenshot({ path: `${OUT}/02-modal.png` });

  await clickByText(page, "button", "Analyze & create ticket");
  const created = await waitForText(page, "Customer request", 25000);
  check("New ticket opens after analysis", created);
  await sleep(800);

  const detailText = await page.evaluate(() => document.body.innerText);
  check("Classification applied (Refund)", /Refund/i.test(detailText));
  check("Escalation triggers shown", /Policy exception/i.test(detailText));
  check("Recommended action is human review", /Needs human review/i.test(detailText));
  check("Knowledge article retrieved", /Knowledge used/i.test(detailText));
  check("Draft banner is clearly AI", /AI draft — not sent/i.test(detailText));
  const reference = (detailText.match(/SP-\d+/) || [])[0] ?? "";
  check("Ticket reference assigned", /^SP-\d+$/.test(reference), reference);
  await page.screenshot({ path: `${OUT}/03-created.png`, fullPage: true });

  // ---- 3. Edit the draft ------------------------------------------------
  const textarea = await page.$('textarea[aria-label="Draft reply"]');
  check("Draft editor present", Boolean(textarea));
  await textarea.click();
  await page.keyboard.down("Control");
  await page.keyboard.press("A");
  await page.keyboard.up("Control");
  await page.keyboard.press("Backspace");
  await page.type(
    'textarea[aria-label="Draft reply"]',
    "Hi Angela,\n\nI'm sorry this has been so frustrating. Your request falls outside our 30-day window, so it needs a supervisor's review before I can confirm anything. I've passed it along and a teammate will follow up.\n\nBest regards,\nNorthwind Support Team",
  );
  await sleep(300);
  const draftValue = await page.$eval('textarea[aria-label="Draft reply"]', (el) => el.value);
  check("Draft editor replaces text cleanly", draftValue.startsWith("Hi Angela,") && !draftValue.includes("I am really sorry"), `${draftValue.slice(0, 40)}…`);
  await clickByText(page, "button", "Save draft");
  const savedOk = await waitForText(page, "Draft saved");
  check("Draft save shows success feedback", savedOk);
  await waitForText(page, "Edited by human");
  check("Draft status becomes edited", true);
  await page.screenshot({ path: `${OUT}/04-edited.png`, fullPage: true });

  // ---- 4. Approve the reply --------------------------------------------
  await clickByText(page, "button", "Approve & send");
  const approvedOk = await waitForText(page, "Human-approved reply", 15000);
  check("Approval produces a human-approved reply", approvedOk);
  const approvedText = await page.evaluate(() => document.body.innerText);
  check("Status moved to In Progress", /In Progress/i.test(approvedText));
  check("Approved reply visible in conversation", /a teammate will follow up/i.test(approvedText));
  const approvedBody = await page.evaluate(() => {
    const panel = Array.from(document.querySelectorAll("section")).find((node) =>
      node.innerText.includes("Human-approved reply"),
    );
    const bubble = panel?.querySelector("div.whitespace-pre-wrap");
    return bubble?.textContent ?? "";
  });
  check(
    "Approved reply renders once, unmodified",
    approvedBody.trim().startsWith("Hi Angela,") && (approvedBody.match(/Hi Angela,/g) || []).length === 1,
    `${(approvedBody.match(/Hi Angela,/g) || []).length} greeting(s), ${approvedBody.length} chars`,
  );
  await page.screenshot({ path: `${OUT}/05-approved.png`, fullPage: true });

  // ---- 5. Resolve -------------------------------------------------------
  await clickByText(page, "button", "Resolve", { exact: true, scope: "main" });
  await sleep(400);
  await clickByText(page, "button", "Confirm resolve", { exact: true, scope: "main" });
  const resolvedOk = await waitForText(page, "Ticket resolved", 15000);
  check("Resolve completes with feedback", resolvedOk);
  await sleep(600);
  const resolvedText = await page.evaluate(() => document.body.innerText);
  check("Reopen control offered when resolved", /Reopen/i.test(resolvedText));

  // BUG-001 regression: a resolved ticket must not offer approval in the UI.
  const approveStillVisible = await page.evaluate(() =>
    Array.from(document.querySelectorAll("button")).some((b) =>
      b.innerText.replace(/\s+/g, " ").trim().toLowerCase() === "approve & send",
    ),
  );
  check("Resolved ticket hides 'Approve & send'", approveStillVisible === false);

  // The draft must no longer be editable: either the read-only draft panel or
  // the human-approved reply panel is shown, but never the editable editor.
  const draftEditorVisible = await page.evaluate(
    () => Boolean(document.querySelector('textarea[aria-label="Draft reply"]')),
  );
  check("Resolved ticket has no editable draft", draftEditorVisible === false);
  check(
    "Resolved ticket shows the approved reply or a read-only draft",
    /read only/i.test(resolvedText) || /Human-approved reply/i.test(resolvedText),
  );

  // BUG-001 regression at the API level. Done from Node (not the page) so the
  // deliberate 409 does not pollute the browser console.
  const ticketId = page.url().split("/").pop();
  const approveResponse = await fetch(`${BASE}/api/tickets/${ticketId}/approve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ body: "late approval" }),
  });
  const approveDetail = (await approveResponse.json()).detail ?? "";
  check(
    "API rejects approval on a resolved ticket",
    approveResponse.status === 409 && /reopen/i.test(approveDetail),
    `${approveResponse.status} ${approveDetail}`,
  );

  // BUG-003 regression: knowledge total must follow the active filter.
  const knowledgeTotals = await page.evaluate(async () => {
    const billing = await (await fetch("/api/knowledge?category=billing")).json();
    const all = await (await fetch("/api/knowledge")).json();
    return { billingTotal: billing.total, billingItems: billing.items.length, allTotal: all.total };
  });
  check(
    "Knowledge total matches the filtered item count",
    knowledgeTotals.billingTotal === knowledgeTotals.billingItems && knowledgeTotals.allTotal === 20,
    `billing=${knowledgeTotals.billingTotal}/${knowledgeTotals.billingItems}, all=${knowledgeTotals.allTotal}`,
  );
  await page.screenshot({ path: `${OUT}/06-resolved.png`, fullPage: true });

  // ---- 6. Filters and search -------------------------------------------
  await page.goto(`${BASE}/inbox`, { waitUntil: "networkidle2" });
  await waitForText(page, "Support Inbox");
  await sleep(500);
  await clickByText(page, "button", "Needs human");
  await sleep(900);
  const filtered = await page.evaluate(() => document.body.innerText);
  const filteredCount = Number((filtered.match(/(\d+) tickets?/i) || [])[1] ?? -1);
  check("Requires-human filter narrows the list", filteredCount > 0 && filteredCount < 10, `${filteredCount} tickets`);

  // Clear the review filter before searching for a routine ticket.
  await clickByText(page, "button", "Needs human");
  await sleep(900);
  await page.type('input[aria-label="Search tickets"]', "Maya");
  await sleep(1400);
  const searched = await page.evaluate(() => document.body.innerText);
  check("Search finds a specific customer", /Maya Chen/i.test(searched));
  await page.screenshot({ path: `${OUT}/07-filters.png` });

  // ---- 7. Open a ticket from the list ----------------------------------
  await page.goto(`${BASE}/inbox`, { waitUntil: "networkidle2" });
  await sleep(600);
  await clickByText(page, "a", "Maya Chen");
  const opened = await waitForText(page, "Customer request", 15000);
  check("Ticket opens from list", opened);
  await sleep(700);
  const mayaText = await page.evaluate(() => document.body.innerText);
  check("Routine ticket shows no escalation", /None detected/i.test(mayaText));
  check("Grounding excerpt displayed", /shipping/i.test(mayaText));

  // ---- 8. Persistence across reload ------------------------------------
  const urlBefore = page.url();
  await page.reload({ waitUntil: "networkidle2" });
  await sleep(1200);
  const afterReload = await page.evaluate(() => document.body.innerText);
  check("Ticket survives a hard reload", /Customer request/i.test(afterReload), urlBefore);

  // ---- 9. Knowledge base -----------------------------------------------
  await page.goto(`${BASE}/knowledge`, { waitUntil: "networkidle2" });
  await waitForText(page, "Knowledge Base");
  await sleep(700);
  const kbText = await page.evaluate(() => document.body.innerText);
  check("Knowledge base lists articles", /20 articles/i.test(kbText));
  await clickByText(page, "button", "30-day refund policy");
  await sleep(700);
  const articleText = await page.evaluate(() => document.body.innerText);
  check("Article opens with full content", /Unused items in their original packaging/i.test(articleText));
  await page.screenshot({ path: `${OUT}/08-knowledge.png` });

  // ---- 10. Metrics reflect the workflow --------------------------------
  await page.goto(`${BASE}/`, { waitUntil: "networkidle2" });
  await sleep(1200);
  const finalText = await page.evaluate(() => document.body.innerText);
  const finalTotal = Number((finalText.match(/TOTAL TICKETS\s*\n?\s*(\d+)/i) || [])[1] ?? -1);
  check("Metrics incremented after creating a ticket", finalTotal === 10, `got ${finalTotal}`);
  const finalResolved = Number((finalText.match(/RESOLVED\s*\n?\s*(\d+)/i) || [])[1] ?? -1);
  check("Resolved count reflects the UI action", finalResolved === 3, `got ${finalResolved}`);
  await page.screenshot({ path: `${OUT}/09-overview-final.png` });

  // ---- 11. Empty state --------------------------------------------------
  await page.goto(`${BASE}/inbox?q=zzzznotfound`, { waitUntil: "networkidle2" });
  await sleep(1000);
  const emptyText = await page.evaluate(() => document.body.innerText);
  check("Empty state shown for no matches", /No tickets match/i.test(emptyText));
  await page.screenshot({ path: `${OUT}/10-empty.png` });
} catch (error) {
  check("Unhandled UI test error", false, error.message);
  await page.screenshot({ path: `${OUT}/error.png` }).catch(() => {});
} finally {
  check("No uncaught page errors", pageErrors.length === 0, pageErrors.join(" | "));
  check("No failed network requests", failedRequests.length === 0, failedRequests.slice(0, 3).join(" | "));
  const realConsoleErrors = consoleErrors.filter((text) => !/favicon/i.test(text));
  check("No console errors", realConsoleErrors.length === 0, realConsoleErrors.slice(0, 3).join(" | "));

  await browser.close();

  const failed = results.filter((r) => !r.ok);
  console.log(`\n${results.length - failed.length}/${results.length} checks passed`);
  fs.writeFileSync(`${OUT}/results.json`, JSON.stringify({ results, consoleErrors, pageErrors, failedRequests }, null, 2));
  process.exit(failed.length === 0 ? 0 : 1);
}