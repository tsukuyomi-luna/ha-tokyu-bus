/* Original HA card. No external requests; provider data comes only from HA. */
class TokyuBusCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
  }
  setConfig(c) {
    if (!c.entity || !c.schedule_entity) throw new Error("entity and schedule_entity are required");
    this.config = c;
    this.shadowRoot.innerHTML = `<style>
      :host{display:block}ha-card{overflow:hidden;border:1px solid var(--divider-color);border-radius:18px;background:var(--ha-card-background,var(--card-background-color));color:var(--primary-text-color)}
      .wrap{padding:22px}header{display:flex;align-items:center;gap:10px}.badge{background:var(--primary-color);color:var(--text-primary-color,#fff);padding:6px 10px;border-radius:7px;font-weight:750}.route{font-size:14px;line-height:1.6;overflow-wrap:anywhere}.muted{color:var(--secondary-text-color);font-size:12px}.timeblock{display:flex;align-items:baseline;gap:12px;margin:22px 0 18px;flex-wrap:wrap}.clock{font-size:44px;letter-spacing:-1px;font-weight:750;font-variant-numeric:tabular-nums}.count{font-size:17px;font-variant-numeric:tabular-nums}.grid{display:grid;grid-template-columns:1fr 1fr;border-top:1px solid var(--divider-color);border-bottom:1px solid var(--divider-color);gap:16px;padding:16px 0}.value{margin-top:5px;font-size:18px;overflow-wrap:anywhere}.track{margin:18px 0;padding:0;list-style:none}.track li{display:flex;align-items:center;gap:12px;min-height:35px;font-size:14px}.dot{width:9px;height:9px;border:2px solid var(--divider-color);border-radius:50%;flex-shrink:0}.next .dot{background:var(--primary-color);border-color:var(--primary-color)}.next{font-weight:750}.passed{color:var(--secondary-text-color)}footer{display:flex;align-items:center;justify-content:space-between;gap:8px;flex-wrap:wrap}button{font:inherit;font-size:13px;padding:10px 12px;border-radius:8px;border:1px solid var(--divider-color);color:var(--primary-text-color);background:transparent;cursor:pointer}button:focus-visible{outline:2px solid var(--primary-color);outline-offset:2px}button:disabled{opacity:.45;cursor:default}.buttons{display:flex;gap:6px}.error{color:var(--error-color);font-size:13px;margin-top:8px}[hidden]{display:none!important}@media(max-width:350px){.wrap{padding:16px}.clock{font-size:38px}.value{font-size:16px}}
    </style><ha-card><div class="wrap">
      <header><span class="badge"></span><div class="route"></div></header>
      <div class="timeblock"><div><div class="muted">発車予定 · 時刻表</div><span class="clock">—</span></div><span class="count"></span></div>
      <div class="grid"><div><div class="muted">実車の到着見込み</div><div class="value arrival">—</div></div><div><div class="muted">混雑</div><div class="value crowd">—</div></div></div>
      <ol class="track" aria-label="バスの通過状況"></ol><p class="empty muted"></p>
      <footer><span class="updated muted"></span><div class="buttons"><button class="start" aria-label="スマホのライブアクティビティを開始">スマホに表示</button><button class="test" aria-label="2分間のライブアクティビティ表示テスト">表示テスト</button><button class="stop" aria-label="ライブアクティビティを終了">終了</button></div></footer><div class="error" role="status"></div>
    </div></ha-card>`;
    this.q(".badge").textContent = c.route || "バス";
    this.q(".route").textContent = c.title || "バス接近情報";
    this.q(".test").hidden = !c.test_script;
    this.q(".test").onclick = () => this.run(c.test_script);
    this.q(".start").hidden = !c.start_script;
    this.q(".stop").hidden = !c.stop_script;
    this.q(".start").onclick = () => this.run(c.start_script);
    this.q(".stop").onclick = () => this.run(c.stop_script);
    this._trackKey = null;
    this.render();
  }
  q(s) {
    return this.shadowRoot.querySelector(s);
  }
  set hass(h) {
    this._hass = h;
    this.render();
  }
  connectedCallback() {
    if (!this.timer) this.timer = setInterval(() => this.render(), 1000);
  }
  disconnectedCallback() {
    clearInterval(this.timer);
    this.timer = null;
  }
  getCardSize() {
    return 5;
  }
  async run(entity) {
    this.q(".error").textContent = "";
    try {
      await this._hass.callService("script", "turn_on", { entity_id: entity });
    } catch {
      this.q(".error").textContent = "送信できませんでした";
    }
  }
  render() {
    if (!this.config || !this._hass || !this.q(".clock")) return;
    const state = this._hass.states[this.config.entity],
      attrs = state?.attributes || {};
    const age = (Date.now() - Date.parse(attrs.retrieved_at)) / 1000;
    const stale =
      !state ||
      state.state === "unavailable" ||
      !Number.isFinite(age) ||
      age > Math.max(120, (attrs.poll_seconds || 30) * 3);
    const dep = this._hass.states[this.config.schedule_entity];
    const when = Date.parse(dep?.state);
    const valid = !stale && Number.isFinite(when);
    this.q(".clock").textContent = valid
      ? new Intl.DateTimeFormat("ja-JP", {
          timeZone: "Asia/Tokyo",
          hour: "2-digit",
          minute: "2-digit",
        }).format(when)
      : "—";
    const sec = Math.ceil((when - Date.now()) / 1000);
    const sameDay =
      valid &&
      new Intl.DateTimeFormat("ja-JP", {
        timeZone: "Asia/Tokyo",
        dateStyle: "short",
      }).format(when) ===
        new Intl.DateTimeFormat("ja-JP", {
          timeZone: "Asia/Tokyo",
          dateStyle: "short",
        }).format(Date.now());
    this.q(".count").textContent = !valid
      ? ""
      : sec < 0
        ? "予定時刻を過ぎました"
        : !sameDay
          ? "翌日以降"
          : sec >= 3600
            ? `あと${Math.floor(sec / 3600)}時間${Math.floor((sec % 3600) / 60)}分`
            : `あと${Math.floor(sec / 60)}:${String(sec % 60).padStart(2, "0")}`;
    const buses = stale ? [] : attrs.buses || [],
      b = buses[0];
    this.q(".arrival").textContent = b ? `約${b.time_left}分` : "情報なし";
    this.q(".crowd").textContent = b
      ? {
          LOW: "空いている",
          NORMAL: "普通",
          HIGH: "混雑",
          UNCLEAR: "不明",
          UNKNOWN: "不明",
        }[b.congestion_level] || "不明"
      : "—";
    this.q(".updated").textContent = stale
      ? "更新できていません"
      : `${Math.max(0, Math.floor(age))}秒前に取得`;
    this.q(".start").disabled = !valid || sec <= 0 || sec > 7200;
    this.q(".start").title = sec > 7200 ? "発車予定の2時間前から表示できます" : "";
    const stops = stale ? [] : attrs.stops || [];
    let i = stops.findIndex((x) => x.status === "NEXT");
    const visible = i < 0 ? [] : stops.slice(Math.max(0, i - 1), i + 3);
    const key = JSON.stringify(visible);
    if (key !== this._trackKey) {
      this._trackKey = key;
      const list = this.q(".track");
      list.replaceChildren();
      for (const stop of visible) {
        const li = document.createElement("li");
        li.className = stop.status === "NEXT" ? "next" : stop.status === "PASSED" ? "passed" : "";
        const dot = document.createElement("span");
        dot.className = "dot";
        dot.setAttribute("aria-hidden", "true");
        const text = document.createElement("span");
        text.textContent = `${stop.stop?.name || "不明"}${stop.status === "NEXT" ? " · 次" : stop.status === "PASSED" ? " · 通過" : ""}`;
        li.append(dot, text);
        list.append(li);
      }
    }
    this.q(".empty").textContent = stale
      ? "接近情報を取得できません"
      : b && !visible.length
        ? "停留所位置は未取得"
        : !b
          ? "接近情報なし"
          : "";
    this.q(".empty").hidden = !!visible.length;
  }
}
if (!customElements.get("tokyu-bus-card")) customElements.define("tokyu-bus-card", TokyuBusCard);
window.customCards = window.customCards || [];
window.customCards.push({
  type: "tokyu-bus-card",
  name: "Tokyu Bus",
  description: "発車予定と接近情報",
});
