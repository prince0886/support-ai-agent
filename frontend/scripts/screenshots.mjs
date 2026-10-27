// Capture clean marketing/README screenshots from the seeded app.
import puppeteer from "puppeteer-core";

const BASE = "http://127.0.0.1:8000";
const CHROME = process.env.CHROME_PATH ?? "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const OUT = "..\\docs\\screenshots";

const browser = await puppeteer.launch({
  executablePath: CHROME,
  headless: "new",
  args: ["--no-sandbox", "--disable-gpu"],
  defaultViewport: { width: 1440, height: 980 },
});
const page = await browser.newPage();
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const shots = [
  ["/", "overview.png"],
  ["/inbox", "inbox.png"],
  ["/inbox/3", "ticket-detail.png"],
  ["/knowledge", "knowledge.png"],
  ["/settings", "settings.png"],
];

for (const [path, file] of shots) {
  await page.goto(`${BASE}${path}`, { waitUntil: "networkidle2" });
  await sleep(1600);
  await page.screenshot({ path: `${OUT}\\${file}` });
  console.log("captured", file);
}

await browser.close();
