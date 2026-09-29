const { chromium } = require("playwright");
const assert = require("node:assert/strict");
const path = require("node:path");
(async () => {
  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage();
    const errors = [];
    page.on("pageerror", (e) => errors.push(e.message));
    await page.setContent(
      "<style>body{margin:12px;background:#eee;color:#222;font:16px sans-serif;--primary-color:#34766a;--divider-color:#ccc;--secondary-text-color:#666;--ha-card-background:#fff;--primary-text-color:#222}</style>",
    );
    await page.addScriptTag({ path: path.resolve("www/tokyu-bus-card.js") });
    await page.evaluate(() => {
      const card = document.createElement("tokyu-bus-card");
      card.setConfig({
        entity: "sensor.bus",
        schedule_entity: "sensor.schedule",
        title: "テスト停留所 → ターミナル",
        route: "系統名",
        start_script: "script.start",
        stop_script: "script.stop",
        test_script: "script.test",
      });
      window.calls = [];
      window.fixture = {
        states: {
          "sensor.bus": {
            state: "4",
            attributes: {
              retrieved_at: new Date().toISOString(),
              poll_seconds: 30,
              buses: [{ time_left: 4, congestion_level: "HIGH" }],
              stops: [
                { status: "PASSED", stop: { name: "前の停留所" } },
                { status: "NEXT", stop: { name: "次の停留所" } },
                { status: "UNPASSED", stop: { name: "その次" } },
              ],
            },
          },
          "sensor.schedule": { state: new Date(Date.now() + 180000).toISOString() },
        },
        callService: async (...args) => window.calls.push(args),
      };
      card.hass = window.fixture;
      document.body.append(card);
      window.card = card;
    });
    for (const width of [320, 390, 800]) {
      await page.setViewportSize({ width, height: 850 });
      assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    }
    const card = page.locator("tokyu-bus-card");
    assert.equal(await card.locator(".arrival").innerText(), "約4分");
    assert.equal(await card.locator(".crowd").innerText(), "混雑");
    assert.equal(await card.locator(".track li").count(), 3);
    await card.locator(".start").click();
    assert.deepEqual(await page.evaluate(() => window.calls[0]), [
      "script",
      "turn_on",
      { entity_id: "script.start" },
    ]);
    await card.locator(".test").click();
    assert.equal(await page.evaluate(() => window.calls[1][2].entity_id), "script.test");
    await page.evaluate(() => {
      window.fixture.states["sensor.bus"].attributes.stops[1].stop.name =
        "<img src=x onerror=alert(1)>";
      window.card.hass = window.fixture;
    });
    assert.equal(await card.locator("img").count(), 0);
    await page.evaluate(() => {
      window.fixture.states["sensor.bus"].attributes.retrieved_at = new Date(
        Date.now() - 180000,
      ).toISOString();
      window.card.hass = window.fixture;
    });
    assert.equal(await card.locator(".clock").innerText(), "—");
    assert.equal(await card.locator(".start").isDisabled(), true);
    await page.evaluate(() => {
      window.fixture.states["sensor.bus"] = {
        state: "unknown",
        attributes: { retrieved_at: new Date().toISOString(), buses: [], stops: [] },
      };
      window.card.hass = window.fixture;
    });
    assert.equal(await card.locator(".empty").innerText(), "接近情報なし");
    await page.setViewportSize({ width: 390, height: 750 });
    await page.screenshot({ path: "/tmp/tokyu-bus-card-preview.png" });
    await page.evaluate(() => window.card.remove());
    assert.equal(await page.evaluate(() => window.card.timer), null);
    assert.deepEqual(errors, []);
    console.log(
      "Card browser checks passed (320/390/800px, state, stale, empty, buttons, XSS, cleanup)",
    );
  } finally {
    await browser.close();
  }
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
