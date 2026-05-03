// 法遵內容（個資、隱私、Cookie、未成年、警語）+ Modal + Cookie banner

const LEGAL_CONTENT = {
  "personal-data": {
    title: "個人資料蒐集告知",
    body: `
<p>依據《個人資料保護法》第 8 條，本系統於使用者主動輸入下列資料時進行蒐集、處理及利用：</p>
<ul>
  <li><strong>身分證字號</strong>：用於計算個人先天磁場與年齡時間軸分析。</li>
  <li><strong>電話號碼</strong>：用於分析該號碼之磁場組合。</li>
  <li><strong>車牌號碼</strong>：用於分析車牌之磁場組合。</li>
</ul>
<p><strong>蒐集目的</strong>：提供數字易經分析服務、智能推薦演算。</p>
<p><strong>利用期間</strong>：分析完成後，輸入欄位即時清空，不於伺服器或瀏覽器留存任何個資。</p>
<p><strong>利用方式</strong>：所有運算於使用者瀏覽器與我方伺服器即時完成，分析結果不寫入資料庫、不傳輸至第三方。</p>
<p><strong>利用對象</strong>：僅限本服務內部運算，不對外提供。</p>
<p><strong>權利行使</strong>：依個資法第 3 條，您得隨時請求查詢、更正、刪除您的個人資料，或停止蒐集、處理及利用。</p>
<p><strong>不提供之影響</strong>：未提供將無法獲得對應的個人化分析結果。</p>
`,
  },
  "privacy": {
    title: "隱私權政策",
    body: `
<h3>1. 適用範圍</h3>
<p>本政策適用於您使用本平台所提供的所有服務。</p>

<h3>2. 資訊蒐集</h3>
<p>本平台僅在您主動輸入時暫存個人輸入資料於瀏覽器記憶體中。一經查詢結束或關閉頁面，資料即清除，不會存入伺服器資料庫。</p>

<h3>3. 自動蒐集資訊</h3>
<p>為維護服務運作，伺服器可能記錄訪問時間、瀏覽器類型、來源 IP（不含個人識別資訊）。</p>

<h3>4. 資料安全</h3>
<p>本平台採 HTTPS 加密傳輸，分析資料不寫入永久儲存。但網路傳輸無法 100% 保證安全，請您自行評估風險。</p>

<h3>5. 資料分享</h3>
<p>本平台<strong>不會</strong>將您的輸入內容分享、出售或轉移給任何第三方。</p>

<h3>6. 您的權利</h3>
<p>您可隨時：</p>
<ul>
  <li>停止使用本服務</li>
  <li>清除瀏覽器快取與 Cookie</li>
  <li>請求說明我們蒐集之資料項目</li>
</ul>

<h3>7. 政策變更</h3>
<p>本政策如有變更，將於本頁更新並標註修訂日期。</p>

<p class="legal-meta">最後更新：2026-05-04</p>
`,
  },
  "cookie": {
    title: "Cookie 政策",
    body: `
<h3>什麼是 Cookie</h3>
<p>Cookie 是儲存在您裝置上的小型文字檔，用於記住您的偏好設定。</p>

<h3>本網站使用的 Cookie 類型</h3>
<table class="legal-table">
  <tr><th>類型</th><th>用途</th><th>保存期限</th></tr>
  <tr><td>必要 Cookie</td><td>維持頁面正常運作（如分頁狀態）</td><td>關閉瀏覽器即清除</td></tr>
  <tr><td>偏好 Cookie</td><td>記住您的同意狀態</td><td>1 年</td></tr>
</table>

<h3>本網站<strong>不</strong>使用</h3>
<ul>
  <li>追蹤分析 Cookie（如 Google Analytics）</li>
  <li>廣告 Cookie</li>
  <li>第三方社交媒體 Cookie</li>
</ul>

<h3>如何拒絕 Cookie</h3>
<p>您可於瀏覽器設定中關閉 Cookie，但部分功能（如記住已同意）將無法運作。</p>

<p class="legal-meta">最後更新：2026-05-04</p>
`,
  },
  "minor": {
    title: "未成年保護政策",
    body: `
<h3>適用對象</h3>
<p>本平台依《兒童及少年福利與權益保障法》制定下列政策。</p>

<h3>未成年使用</h3>
<ul>
  <li>未滿 <strong>18 歲</strong> 之未成年人，使用本服務應取得法定代理人（父母或監護人）之同意。</li>
  <li>未滿 <strong>7 歲</strong> 之兒童，請由法定代理人陪同並代為操作。</li>
</ul>

<h3>家長 / 監護人責任</h3>
<p>請家長協助未成年子女理解：</p>
<ul>
  <li>本系統僅為命理數字分析參考，<strong>非醫療、教育或人生決策建議</strong>。</li>
  <li>分析結果僅供娛樂與自我了解，不應據以做出重大決定。</li>
  <li>切勿因分析結果產生焦慮或自我否定。</li>
</ul>

<h3>資料保護</h3>
<p>本平台不主動蒐集未成年人之個人資料，亦不針對未成年提供任何加值服務。</p>

<p class="legal-meta">最後更新：2026-05-04</p>
`,
  },
  "disclaimer": {
    title: "使用警語",
    body: `
<div class="legal-warning">
  <p><strong>⚠️ 重要聲明</strong></p>
  <p>數字易經分析屬於<strong>傳統命理參考工具</strong>，<strong>非科學依據</strong>，亦非醫療、心理諮商、財務或法律建議。</p>
</div>

<h3>使用須知</h3>
<ol>
  <li><strong>僅供參考、自我了解、娛樂用途</strong>，請理性看待結果。</li>
  <li><strong>不構成任何決策依據</strong>——重大事項（婚姻、健康、投資、簽約等）請諮詢相關專業人士。</li>
  <li>分析結果<strong>無法 100% 準確預測</strong>個人運勢或事件發展。</li>
  <li>切勿因分析結果而過度焦慮、自我否定或對他人產生偏見。</li>
  <li>本平台所提供的「智能建議」（號碼推薦）僅為磁場組合計算，<strong>不保證實際效果</strong>。</li>
</ol>

<h3>免責聲明</h3>
<p>使用者依本平台分析結果所做之任何決策、行為或衍生後果，<strong>本平台概不承擔任何責任</strong>。</p>

<p class="legal-meta">最後更新：2026-05-04</p>
`,
  },
};

// ── Modal 控制 ──
function openLegal(key) {
  const data = LEGAL_CONTENT[key];
  if (!data) return;
  document.getElementById("legal-modal-title").textContent = data.title;
  document.getElementById("legal-modal-body").innerHTML = data.body;
  document.getElementById("legal-modal").hidden = false;
  document.body.style.overflow = "hidden";
}

function closeLegal() {
  document.getElementById("legal-modal").hidden = true;
  document.body.style.overflow = "";
}

document.addEventListener("click", (e) => {
  const trigger = e.target.closest("[data-legal]");
  if (trigger) {
    e.preventDefault();
    openLegal(trigger.dataset.legal);
    return;
  }
  if (e.target.closest("[data-close]")) {
    closeLegal();
  }
});

document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") closeLegal();
});

// ── Cookie 同意條 ──
const COOKIE_KEY = "cookie-consent-v1";
const banner = document.getElementById("cookie-banner");
const acceptBtn = document.getElementById("cookie-accept");

if (banner && acceptBtn) {
  if (!localStorage.getItem(COOKIE_KEY)) {
    banner.hidden = false;
  }
  acceptBtn.addEventListener("click", () => {
    localStorage.setItem(COOKIE_KEY, "accepted-" + Date.now());
    banner.hidden = true;
  });
}
