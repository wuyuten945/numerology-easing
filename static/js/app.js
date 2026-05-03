// 數字易經分析 Web UI

const GOOD = ["天醫", "生氣", "延年", "伏位"];
const BAD = ["絕命", "五鬼", "六煞", "禍害"];
const ALL = [...GOOD, ...BAD];

const MAGNET_INFO = {
  "天醫": { kind: "吉", brief: "貴人財富", desc: "貴人相助、財運穩固、化險為夷" },
  "生氣": { kind: "吉", brief: "機會人緣", desc: "正能量、機會多、人緣亨通" },
  "延年": { kind: "吉", brief: "長久穩定", desc: "感情和諧、健康長壽、做事持久" },
  "伏位": { kind: "吉", brief: "平穩守成", desc: "按部就班、安守本分、穩中求進" },
  "絕命": { kind: "凶", brief: "破財損傷", desc: "破財、健康危機、意外損失" },
  "五鬼": { kind: "凶", brief: "是非小人", desc: "口舌官司、小人作祟、心神不寧" },
  "六煞": { kind: "凶", brief: "感情糾葛", desc: "桃花是非、人際困擾、感情風波" },
  "禍害": { kind: "凶", brief: "爭執病災", desc: "病災、爭執糾紛、運勢起伏" },
};

const charts = {};

// 凶星 → 對應吉星（用於智能建議）
const COUNTER_MAGNET = {
  "絕命": "天醫",  // A1: 天醫消絕命
  "五鬼": "生氣",  // A5 三連消五鬼，主磁場 = 生氣
  "六煞": "延年",  // A3: 延年壓六煞
  "禍害": "生氣",  // A4: 生氣組合消禍害
};

// 吉星 → 它可以消的凶星（反向）
const GOOD_COUNTERS_BAD = {
  "天醫": ["絕命"],
  "延年": ["六煞"],
  "生氣": ["禍害", "五鬼"],
};

// 儲存最近一次的個人分析結果（智能建議會讀取）
let personalAnalysis = null;

// ─── Tabs ─────────────────────────────────────
document.querySelectorAll(".tab-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".tab-panel").forEach(p => p.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById("tab-" + btn.dataset.tab).classList.add("active");
  });
});

async function apiPost(url, body) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return res.json();
}

const escapeHtml = s => String(s).replace(/[&<>"']/g, c => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
}[c]));

const showError = (el, msg) => el.innerHTML = `<div class="error">${escapeHtml(msg)}</div>`;
const showLoading = el => el.innerHTML = `<div class="loading">分析中…</div>`;

// ─── 渲染：磁場分析卡片 ──────────────────────
function renderAnalysis(result, label, chartId) {
  if (result.error) return `<div class="error">${escapeHtml(label)}：${escapeHtml(result.error)}</div>`;

  // 配對 pills（顯示磁場名稱 + 簡述）
  const pairs = (result.pairs || []).filter(p => !p.extended);
  const pillsHtml = pairs.map(p => {
    let cls = "neutral";
    if (GOOD.includes(p.magnet)) cls = "good";
    else if (BAD.includes(p.magnet)) cls = "bad";
    if (!(p.active ?? true)) cls += " faded";
    let note = "";
    if (p.magnet === "伏位" && p.continues) note = `（延續${p.continues}）`;
    const info = MAGNET_INFO[p.magnet];
    const briefText = info ? `・${info.brief}` : "";
    const display = p.raw_pair !== p.after_assimilation
      ? `${p.raw_pair}→${p.after_assimilation}`
      : p.raw_pair;
    return `<span class="pair-pill ${cls}" title="${info ? escapeHtml(info.desc) : ''}"><span class="num">${escapeHtml(display)}</span><span class="magnet">${escapeHtml(p.magnet)}${escapeHtml(briefText)}${escapeHtml(note)}</span></span>`;
  }).join("");

  // 磁場格（含意義說明）
  const counts = result.magnet_count || {};
  const magnetGrid = ALL.map(m => {
    const n = counts[m] || 0;
    const info = MAGNET_INFO[m];
    const cls = (n === 0 ? "zero " : "") + (GOOD.includes(m) ? "good" : "bad");
    const tag = info.kind === "吉" ? "吉" : "凶";
    return `
      <div class="magnet-cell ${cls}">
        <div class="cell-head">
          <span class="kind">${tag}</span>
          <span class="name">${m}</span>
          <span class="count">${n}</span>
        </div>
        <div class="meaning">${info.desc}</div>
      </div>
    `;
  }).join("");

  // 伏位細分（去除「延續XX」前綴的字串重組成標籤）
  const fb = result.fuwei_breakdown || {};
  const fbHtml = Object.keys(fb).length ? `
    <div class="section-label">伏位細分</div>
    <div class="notes">
      ${Object.entries(fb).map(([k, v]) =>
        `<span class="note-tag">${k === "純伏位" ? "純伏位" : `延續${escapeHtml(k)}`} <strong>×${v}</strong></span>`
      ).join("")}
    </div>` : "";

  // 能量強化（直接列重複次數，不顯示 "強化標記" 等技術用語）
  const marks = result.duplicate_marks || [];
  const marksHtml = marks.length ? `
    <div class="section-label">重複磁場</div>
    <div class="notes">
      ${marks.map(m => `<span class="note-tag">${escapeHtml(m)}</span>`).join("")}
    </div>` : "";

  return `
    <div class="card">
      <div class="card-title">${escapeHtml(label)}</div>
      <div class="card-subtitle">${escapeHtml(result.input)}</div>

      <div class="section-label">磁場分布</div>
      <div class="magnet-grid">${magnetGrid}</div>
      <div class="chart-container"><canvas id="${chartId}"></canvas></div>

      <div class="section-label">逐對配對</div>
      <div class="pair-row">${pillsHtml}</div>

      ${fbHtml}
      ${marksHtml}
    </div>
  `;
}

function drawMagnetChart(canvasId, magnetCount) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  if (charts[canvasId]) charts[canvasId].destroy();
  const ctx = canvas.getContext("2d");
  charts[canvasId] = new Chart(ctx, {
    type: "bar",
    data: {
      labels: ALL,
      datasets: [{
        data: ALL.map(m => magnetCount[m] || 0),
        backgroundColor: ALL.map(m => GOOD.includes(m) ? "#059669" : "#dc2626"),
        borderRadius: 4,
        maxBarThickness: 36,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: { padding: 8 } },
      scales: {
        y: { beginAtZero: true, ticks: { stepSize: 1, precision: 0 }, grid: { color: "#f3f4f6" } },
        x: { grid: { display: false } },
      },
    },
  });
}

// ─── 渲染：年齡分區（重疊主磁場 + 表格） ───
function renderAgeMapping(am) {
  if (am.error) return `<div class="error">${escapeHtml(am.error)}</div>`;

  const ranges = am.primary_ranges || [];
  const maxAge = Math.max(70, ...ranges.map(r => r.end));
  const axisTicks = [0, 10, 20, 30, 40, 50, 60, 70].filter(a => a <= maxAge);
  const axisHtml = `<div class="timeline-axis">${axisTicks.map(a => `<span>${a}</span>`).join("")}</div>`;

  const rangeBars = ranges.map(r => {
    const left = (r.start / maxAge) * 100;
    const width = ((r.end - r.start) / maxAge) * 100;
    const cls = GOOD.includes(r.magnet) ? `good-${r.magnet}` : `bad-${r.magnet}`;
    const info = MAGNET_INFO[r.magnet];
    const brief = info ? info.brief : "";
    return `
      <div class="timeline-row">
        <div class="timeline-label">
          <div class="tl-magnet">${escapeHtml(r.magnet)}</div>
          <div class="tl-brief">${escapeHtml(brief)}</div>
        </div>
        <div class="timeline-track">
          <div class="timeline-bar ${cls}" style="left:${left}%;width:${width}%">${r.start}–${r.end}</div>
        </div>
      </div>
    `;
  }).join("");

  // 詳細年齡表（顯示磁場意義）
  const tlRows = (am.timeline || [])
    .filter(e => e.age_start <= 70)
    .map(e => {
      let note = "";
      if (e.magnet === "伏位" && e.continues) note = `延續${e.continues}`;
      const cls = GOOD.includes(e.magnet) ? "good" : (BAD.includes(e.magnet) ? "bad" : "");
      const info = MAGNET_INFO[e.magnet];
      const meaning = info ? info.desc : "";
      const noteStr = note ? `（${note}）` : "";
      return `
        <tr>
          <td class="age-col">${e.age_start}–${e.age_end} 歲</td>
          <td class="pair-col">${escapeHtml(e.pair)}</td>
          <td class="magnet-col ${cls}">${escapeHtml(e.magnet)}</td>
          <td class="note-col">${escapeHtml(meaning)}${escapeHtml(noteStr)}</td>
        </tr>
      `;
    }).join("");

  return `
    <div class="card">
      <div class="card-title">年齡分區</div>
      <div class="card-subtitle">${escapeHtml(am.id_decoded)}</div>

      <div class="section-label">主磁場影響範圍（可重疊）</div>
      ${axisHtml}
      <div class="timeline-container">${rangeBars}</div>

      <div class="section-label">年齡細節</div>
      <div class="age-table-wrap">
        <table class="age-table">
          <thead><tr><th>年齡</th><th>數字組</th><th>磁場</th><th>說明</th></tr></thead>
          <tbody>${tlRows}</tbody>
        </table>
      </div>
    </div>
  `;
}

// ─── 自動分析 ───────────────────────────────
document.getElementById("form-auto").addEventListener("submit", async e => {
  e.preventDefault();
  const fd = new FormData(e.target);
  const body = {
    id: fd.get("id").trim(),
    phone: fd.get("phone").trim(),
    license: fd.get("license").trim(),
  };
  if (!body.id && !body.phone && !body.license) {
    showError(document.getElementById("result-auto"), "請至少輸入一項");
    return;
  }
  const container = document.getElementById("result-auto");
  showLoading(container);
  const data = await apiPost("/api/auto", body);

  let html = "";
  // 綜合儀表面板（top-level summary）
  if (data.id || data.phone || data.license) {
    html += renderPersonalSummary(data);
  }
  if (data.id) html += renderAnalysis(data.id, "身分證", "chart-auto-id");
  if (data.id_error) html += `<div class="error">身分證：${escapeHtml(data.id_error)}</div>`;
  if (data.age_mapping) html += renderAgeMapping(data.age_mapping);
  if (data.phone) html += renderAnalysis(data.phone, "電話", "chart-auto-phone");
  if (data.phone_error) html += `<div class="error">電話：${escapeHtml(data.phone_error)}</div>`;
  if (data.license) html += renderAnalysis(data.license, "車牌", "chart-auto-license");
  if (data.license_error) html += `<div class="error">車牌：${escapeHtml(data.license_error)}</div>`;
  container.innerHTML = html;

  // 繪製 charts
  if (data.id || data.phone || data.license) {
    const total = aggregatePersonalMagnets(data);
    const goodSum = GOOD.reduce((s, m) => s + (total[m] || 0), 0);
    const badSum = BAD.reduce((s, m) => s + (total[m] || 0), 0);
    drawSummaryDonut(goodSum, badSum);
  }
  if (data.id) drawMagnetChart("chart-auto-id", data.id.magnet_count);
  if (data.phone) drawMagnetChart("chart-auto-phone", data.phone.magnet_count);
  if (data.license) drawMagnetChart("chart-auto-license", data.license.magnet_count);

  // 儲存供智能建議使用
  if (data.id || data.phone || data.license) {
    personalAnalysis = data;
  }

  // 隱私保護：分析完立即清空所有輸入欄位（防個資殘留）
  e.target.reset();
});

// 將個人分析的 id/phone/license 磁場數量加總
function aggregatePersonalMagnets(analysis) {
  const total = {};
  for (const key of ["id", "phone", "license"]) {
    const counts = (analysis[key] || {}).magnet_count || {};
    for (const [m, n] of Object.entries(counts)) {
      if (m === "中性") continue;
      total[m] = (total[m] || 0) + n;
    }
  }
  return total;
}

// ─── 綜合儀表面板 ─────────────────────────────
function renderPersonalSummary(analysis) {
  const total = aggregatePersonalMagnets(analysis);
  const goodSum = GOOD.reduce((s, m) => s + (total[m] || 0), 0);
  const badSum = BAD.reduce((s, m) => s + (total[m] || 0), 0);
  const totalSum = goodSum + badSum;
  if (totalSum === 0) return "";

  const score = Math.round((goodSum / totalSum) * 100);
  const maxCount = Math.max(1, ...ALL.map(m => total[m] || 0));

  // SVG 半圓指針儀表
  const angleRad = Math.PI * (1 - score / 100);
  const pointerLen = 78;
  const px = 100 + pointerLen * Math.cos(angleRad);
  const py = 110 - pointerLen * Math.sin(angleRad);

  // 評等
  let level, levelClass;
  if (score >= 75) { level = "極佳"; levelClass = "good"; }
  else if (score >= 60) { level = "良好"; levelClass = "good"; }
  else if (score >= 45) { level = "持平"; levelClass = "neutral"; }
  else if (score >= 30) { level = "偏弱"; levelClass = "weak"; }
  else { level = "需注意"; levelClass = "bad"; }

  // 8 磁場音量條
  const barsHtml = ALL.map(m => {
    const n = total[m] || 0;
    const pct = (n / maxCount) * 100;
    const cls = GOOD.includes(m) ? "good" : "bad";
    const info = MAGNET_INFO[m];
    return `
      <div class="vol-bar">
        <div class="vol-track">
          <div class="vol-fill vol-${cls}" style="height: ${pct}%">
            ${n > 0 ? `<span class="vol-count">${n}</span>` : ""}
          </div>
        </div>
        <div class="vol-label">${m}</div>
        <div class="vol-brief">${info ? info.brief : ""}</div>
      </div>
    `;
  }).join("");

  // 重點摘要：最強吉星、最強凶星
  const strongestGood = GOOD
    .map(m => ({ m, n: total[m] || 0 }))
    .filter(x => x.n > 0)
    .sort((a, b) => b.n - a.n)[0];
  const strongestBad = BAD
    .map(m => ({ m, n: total[m] || 0 }))
    .filter(x => x.n > 0)
    .sort((a, b) => b.n - a.n)[0];

  const insightsHtml = `
    ${strongestGood ? `
      <div class="insight insight-good">
        <div class="insight-head">
          <span class="insight-tag">最強吉星</span>
          <span class="insight-value">${strongestGood.m} ×${strongestGood.n}</span>
        </div>
        <div class="insight-desc">${MAGNET_INFO[strongestGood.m].desc}</div>
      </div>
    ` : ""}
    ${strongestBad ? `
      <div class="insight insight-bad">
        <div class="insight-head">
          <span class="insight-tag">最需注意</span>
          <span class="insight-value">${strongestBad.m} ×${strongestBad.n}</span>
        </div>
        <div class="insight-desc">${MAGNET_INFO[strongestBad.m].desc}</div>
      </div>
    ` : ""}
  `;

  return `
    <div class="card summary-card">
      <div class="card-title">綜合磁場儀表</div>
      <div class="card-subtitle">身分證・電話・車牌 整合分析</div>

      <div class="dash-row">
        <div class="gauge-wrap">
          <svg viewBox="0 0 200 130" class="fortune-gauge">
            <path d="M 22 110 A 78 78 0 0 1 178 110" stroke="#e6e8eb" stroke-width="14" fill="none" stroke-linecap="round"/>
            <path d="M 22 110 A 78 78 0 0 1 60 41" stroke="#dc2626" stroke-width="14" fill="none" stroke-linecap="round"/>
            <path d="M 60 41 A 78 78 0 0 1 100 32" stroke="#f59e0b" stroke-width="14" fill="none" stroke-linecap="round"/>
            <path d="M 100 32 A 78 78 0 0 1 140 41" stroke="#84cc16" stroke-width="14" fill="none" stroke-linecap="round"/>
            <path d="M 140 41 A 78 78 0 0 1 178 110" stroke="#059669" stroke-width="14" fill="none" stroke-linecap="round"/>
            <line x1="100" y1="110" x2="${px.toFixed(1)}" y2="${py.toFixed(1)}" stroke="#1a1d21" stroke-width="3" stroke-linecap="round"/>
            <circle cx="100" cy="110" r="7" fill="#1a1d21"/>
            <circle cx="100" cy="110" r="3" fill="#fff"/>
          </svg>
          <div class="gauge-readout">
            <div class="gauge-score ${levelClass}">${score}<span class="gauge-pct">%</span></div>
            <div class="gauge-level ${levelClass}">${level}</div>
            <div class="gauge-caption">吉星比例</div>
          </div>
        </div>

        <div class="donut-wrap">
          <canvas id="donut-summary"></canvas>
          <div class="donut-center">
            <div class="donut-num">${goodSum} <span class="vs">/</span> ${badSum}</div>
            <div class="donut-cap">吉 / 凶</div>
          </div>
        </div>
      </div>

      <div class="section-label">磁場強度</div>
      <div class="bars-row">${barsHtml}</div>

      <div class="section-label">重點摘要</div>
      <div class="insights">${insightsHtml}</div>
    </div>
  `;
}

function drawSummaryDonut(goodSum, badSum) {
  const canvas = document.getElementById("donut-summary");
  if (!canvas) return;
  if (charts["donut-summary"]) charts["donut-summary"].destroy();
  charts["donut-summary"] = new Chart(canvas.getContext("2d"), {
    type: "doughnut",
    data: {
      labels: ["吉星", "凶星"],
      datasets: [{
        data: [goodSum, badSum],
        backgroundColor: ["#059669", "#dc2626"],
        borderWidth: 0,
      }],
    },
    options: {
      cutout: "72%",
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: { padding: 8 } },
    },
  });
}

// ─── 進階分析（最多 3 組，合併後算交互作用）───
document.getElementById("form-manual").addEventListener("submit", async e => {
  e.preventDefault();
  const fd = new FormData(e.target);
  const inputs = [fd.get("input1"), fd.get("input2"), fd.get("input3")]
    .map(s => (s || "").trim())
    .filter(Boolean);
  if (!inputs.length) {
    showError(document.getElementById("result-manual"), "請至少輸入一組");
    return;
  }
  const container = document.getElementById("result-manual");
  showLoading(container);

  const individual = await Promise.all(
    inputs.map(input => apiPost("/api/analyze", { input, mode: "general" }))
  );
  const combinedInput = inputs.join("");
  const combined = inputs.length > 1
    ? await apiPost("/api/analyze", { input: combinedInput, mode: "general" })
    : individual[0];

  let html = "";

  // 多組時：先列「個別 vs 合併」對照表
  if (inputs.length > 1) {
    const fmtCounts = (counts) => {
      const items = Object.entries(counts || {})
        .filter(([k, v]) => v > 0 && k !== "中性")
        .map(([k, v]) => {
          const cls = GOOD.includes(k) ? "good" : "bad";
          return `<span class="seg-tag ${cls}">${escapeHtml(k)} ${v}</span>`;
        });
      return items.join(" ") || `<span class="seg-tag empty">—</span>`;
    };

    html += `
      <div class="card">
        <div class="card-title">交互作用總覽</div>
        <div class="card-subtitle">${inputs.length} 組號碼合併分析</div>
        <div class="seg-list">
          ${inputs.map((s, i) => `
            <div class="seg-row">
              <span class="seg-label">號碼 ${i + 1}</span>
              <span class="seg-value">${escapeHtml(s)}</span>
              <span class="seg-counts">${fmtCounts(individual[i].magnet_count)}</span>
            </div>
          `).join("")}
          <div class="seg-row seg-merged">
            <span class="seg-label">合併</span>
            <span class="seg-value">${escapeHtml(combinedInput)}</span>
            <span class="seg-counts">${fmtCounts(combined.magnet_count)}</span>
          </div>
        </div>
        <div class="seg-note">
          合併分析會跨號碼套用相剋（A1 天醫消絕命、A3 延年壓六煞）、
          相鄰絕命連鎖加倍、生氣天醫延年消五鬼等規則，
          反映三組號碼的真實互動結果。
        </div>
      </div>
    `;
  }

  html += renderAnalysis(combined, inputs.length > 1 ? "合併分析" : "分析結果", "chart-manual");
  container.innerHTML = html;
  if (!combined.error) drawMagnetChart("chart-manual", combined.magnet_count);

  // 隱私保護：分析完立即清空輸入欄位
  e.target.reset();
});

// ─── 視覺化：手機與車牌 ───────────────────────
function renderPhoneGraphic(number) {
  let display = number;
  if (number.length === 10) {
    display = `${number.slice(0,4)}-${number.slice(4,7)}-${number.slice(7)}`;
  } else if (number.length === 9) {
    display = `${number.slice(0,3)}-${number.slice(3,6)}-${number.slice(6)}`;
  }
  // iPhone 整機外觀：機身 + 側鍵 + 動態島 + 螢幕 + Home 指示條
  return `
    <div class="phone-graphic">
      <div class="phone-frame">
        <div class="phone-btn phone-btn-mute"></div>
        <div class="phone-btn phone-btn-volup"></div>
        <div class="phone-btn phone-btn-voldown"></div>
        <div class="phone-btn phone-btn-power"></div>
        <div class="phone-screen">
          <div class="phone-island">
            <div class="phone-camera"></div>
          </div>
          <div class="phone-status">
            <span>9:41</span>
            <span class="phone-icons">●●●●</span>
          </div>
          <div class="phone-num-block">
            <div class="phone-cap">建議號碼</div>
            <div class="phone-number">${escapeHtml(display)}</div>
          </div>
          <div class="phone-home-bar"></div>
        </div>
      </div>
    </div>
  `;
}

function renderPlateGraphic(number) {
  let prefix = "", suffix = "";
  let i = 0;
  while (i < number.length && /[A-Za-z]/.test(number[i])) i++;
  prefix = number.slice(0, i);
  suffix = number.slice(i);
  const display = prefix && suffix ? `${prefix}-${suffix}` : number;
  // 台灣自小客車牌：上方兩長橢圓螺絲孔；數字下方三朵梅花（左紫、中灰、右紫）
  return `
    <div class="plate-graphic">
      <div class="plate-tw">
        <div class="plate-screws">
          <div class="plate-screw"></div>
          <div class="plate-screw"></div>
        </div>
        <div class="plate-number">${escapeHtml(display)}</div>
        <div class="plate-flowers">
          ${plumBlossomSvg("#c4b5fd")}
          ${plumBlossomSvg("#d1d5db")}
          ${plumBlossomSvg("#c4b5fd")}
        </div>
      </div>
    </div>
  `;
}

function plumBlossomSvg(petalColor) {
  return `
    <svg class="plum" viewBox="0 0 40 40" xmlns="http://www.w3.org/2000/svg">
      <g fill="${petalColor}">
        <circle cx="20" cy="9"  r="6.5"/>
        <circle cx="30.5" cy="16" r="6.5"/>
        <circle cx="26.5" cy="28" r="6.5"/>
        <circle cx="13.5" cy="28" r="6.5"/>
        <circle cx="9.5"  cy="16" r="6.5"/>
      </g>
      <circle cx="20" cy="20" r="3" fill="#fde68a"/>
      <g fill="#a16207" opacity="0.8">
        <circle cx="20" cy="16.5" r="0.7"/>
        <circle cx="22.5" cy="20" r="0.7"/>
        <circle cx="17.5" cy="20" r="0.7"/>
        <circle cx="20" cy="22.5" r="0.7"/>
        <circle cx="22" cy="18" r="0.7"/>
        <circle cx="18" cy="18" r="0.7"/>
        <circle cx="22" cy="22" r="0.7"/>
        <circle cx="18" cy="22" r="0.7"/>
      </g>
    </svg>
  `;
}

// 根據用途調整長度上限與開頭 placeholder
const _purposeSelect = document.querySelector("#form-recommend select[name='purpose']");
const _lengthInput = document.querySelector("#form-recommend input[name='length']");
const _prefixInput = document.querySelector("#form-recommend input[name='prefix']");

function updateRecommendLimits() {
  const p = _purposeSelect.value;
  if (p === "license") {
    _lengthInput.max = 7;
    if (parseInt(_lengthInput.value) > 7) _lengthInput.value = 7;
    _prefixInput.placeholder = "如 ABC、AAA（監理站發的英文字）";
  } else if (p === "phone") {
    _lengthInput.max = 12;
    _prefixInput.placeholder = "如 09";
  } else {
    _lengthInput.max = 12;
    _prefixInput.placeholder = "";
  }
}
_purposeSelect.addEventListener("change", updateRecommendLimits);
updateRecommendLimits();

// ─── 智能建議（基於個人分析自動避凶補吉） ───
document.getElementById("form-recommend").addEventListener("submit", async e => {
  e.preventDefault();
  const fd = new FormData(e.target);
  const container = document.getElementById("result-recommend");

  if (!personalAnalysis) {
    showError(container, "請先在「個人分析」分頁完成身分證／電話／車牌分析，建議才能依您的磁場狀況客製。");
    return;
  }

  // 從個人分析推導 exclude / require
  const totalCounts = aggregatePersonalMagnets(personalAnalysis);
  const exclude = [];
  const require = [];
  for (const bad of BAD) {
    if ((totalCounts[bad] || 0) > 0) {
      exclude.push(bad);
      const counter = COUNTER_MAGNET[bad];
      if (counter && !require.includes(counter)) require.push(counter);
    }
  }

  let userPrefix = fd.get("prefix").trim();
  const prefixHasLetter = /[A-Za-z]/.test(userPrefix);
  if (prefixHasLetter) userPrefix = userPrefix.toUpperCase();

  showLoading(container);

  // 先分析開頭本身：找出開頭強制帶入的凶星，把它們從排除清單中移除
  // （因為開頭一旦帶入，suffix 怎麼配都無法避開 → 強制濾掉會 0 候選）
  let prefixForcedBad = [];
  if (userPrefix.length >= 2) {
    const pa = await apiPost("/api/analyze", { input: userPrefix, mode: "general" });
    if (!pa.error) {
      const pc = pa.magnet_count || {};
      prefixForcedBad = BAD.filter(m => (pc[m] || 0) > 0);
    }
  }
  const finalExclude = exclude.filter(m => !prefixForcedBad.includes(m));
  const finalRequire = require;

  const data = await apiPost("/api/recommend", {
    purpose: fd.get("purpose"),
    length: parseInt(fd.get("length")),
    prefix: userPrefix,
    exclude_magnets: finalExclude,
    require_magnets: finalRequire,
    top_n: 5,
  });

  if (data.error) { showError(container, data.error); return; }
  const recs = data.recommendations || [];

  // 個人分析摘要 + 建議邏輯
  const detectedBad = BAD
    .filter(m => (totalCounts[m] || 0) > 0)
    .map(m => `<span class="seg-tag bad">${m} ${totalCounts[m]}</span>`)
    .join(" ") || `<span class="seg-tag empty">無凶星</span>`;

  const reinforceGood = require.length
    ? require.map(m => `<span class="seg-tag good">${m}</span>`).join(" ")
    : `<span class="seg-tag empty">—</span>`;

  const ruleNotes = [];
  if (exclude.includes("絕命")) ruleNotes.push("天醫消絕命：建議含「13/31/68/86/49/94/27/72」");
  if (exclude.includes("六煞")) ruleNotes.push("延年壓六煞：建議含「19/91/78/87/34/43/26/62」");
  if (exclude.includes("禍害")) ruleNotes.push("生氣消禍害：建議含「14/41/67/76/39/93/28/82」");
  if (exclude.includes("五鬼")) ruleNotes.push("生氣天醫延年連消五鬼：建議含「14+13+19」這類連續組合");

  const summaryCard = `
    <div class="card">
      <div class="card-title">建議邏輯（依您的個人分析）</div>
      <div class="seg-list">
        <div class="seg-row">
          <span class="seg-label">您的凶星</span>
          <span class="seg-counts">${detectedBad}</span>
        </div>
        <div class="seg-row seg-merged">
          <span class="seg-label">需加強</span>
          <span class="seg-counts">${reinforceGood}</span>
        </div>
      </div>
      ${ruleNotes.length ? `<div class="seg-note">${ruleNotes.map(n => `・${escapeHtml(n)}`).join("<br>")}</div>` : ""}
    </div>
  `;

  if (!recs.length) {
    container.innerHTML = summaryCard + `
      <div class="card"><div class="loading">沒有同時滿足避開凶星 + 加強吉星的號碼，請放寬「開頭」或「長度」條件。</div></div>
    `;
    return;
  }

  const purpose = fd.get("purpose");

  // 對每個推薦：列出含哪些吉星，以及這些吉星能消除您身上的哪些凶星
  const items = recs.map(r => {
    const counts = r.magnet_count || {};
    const goodPresent = GOOD
      .filter(g => (counts[g] || 0) > 0)
      .map(g => `${g}×${counts[g]}`);
    const badsCancelled = new Set();
    for (const [good, bads] of Object.entries(GOOD_COUNTERS_BAD)) {
      if ((counts[good] || 0) > 0) {
        for (const bad of bads) {
          if ((totalCounts[bad] || 0) > 0) badsCancelled.add(bad);
        }
      }
    }
    const cancelStr = badsCancelled.size
      ? [...badsCancelled].join("、")
      : "—";
    const goodStr = goodPresent.length ? goodPresent.join("、") : "—";

    // 視覺化容器：電話 → 手機圖形；車牌 → 台灣自小客車牌；其他 → 純文字
    let visual;
    if (purpose === "phone") {
      visual = renderPhoneGraphic(r.number);
    } else if (purpose === "license") {
      visual = renderPlateGraphic(r.number);
    } else {
      let numHtml;
      if (userPrefix && r.number.startsWith(userPrefix)) {
        const suffix = r.number.slice(userPrefix.length);
        numHtml = `<span class="num-prefix">${escapeHtml(userPrefix)}</span><span class="num-suffix">${escapeHtml(suffix)}</span>`;
      } else {
        numHtml = escapeHtml(r.number);
      }
      visual = `<div class="rec-line">建議號碼可以有 <strong class="number">${numHtml}</strong></div>`;
    }

    return `
      <li class="recommend-item rec-visual rec-${purpose}">
        <span class="rank">${r.rank}</span>
        <div class="rec-content">
          ${visual}
          <div class="rec-line rec-detail">含 <strong>${escapeHtml(goodStr)}</strong>，以消除您身上的 <strong class="bad-text">${escapeHtml(cancelStr)}</strong></div>
        </div>
      </li>
    `;
  }).join("");

  let prefixNote = "";
  if (userPrefix) {
    const enc = prefixHasLetter ? "（每個英文字依編號轉為 2 位數字）" : "";
    prefixNote = `磁場分析含您輸入的開頭「${escapeHtml(userPrefix)}」${enc}　|　`;
  }
  const forcedNote = prefixForcedBad.length
    ? `開頭已強制帶入：${prefixForcedBad.join("、")}（無法避開，已從排除清單移除）　|　`
    : "";
  const avoidStr = finalExclude.join("、") || "—";
  const reinforceStr = finalRequire.join("、") || "—";
  container.innerHTML = summaryCard + `
    <div class="card">
      <div class="card-header">
        <div class="card-title">建議使用的號碼</div>
        <button type="button" class="refresh-btn" onclick="document.getElementById('form-recommend').requestSubmit()">再換一組號碼</button>
      </div>
      <div class="card-subtitle">${prefixNote}${forcedNote}已避開：${avoidStr}　強化：${reinforceStr}</div>
      <ul class="recommend-list">${items}</ul>
    </div>
  `;
});
