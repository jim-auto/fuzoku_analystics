const COLORS = ["#6c8cff", "#ff7eb3", "#4ade80", "#fbbf24", "#a78bfa"];

function fmt(n) {
  if (n == null) return "—";
  return n.toLocaleString("ja-JP");
}

function fmtYen(n) {
  if (n == null) return "—";
  return `${n.toLocaleString("ja-JP")}円`;
}

function setupAgeGate() {
  const gate = document.getElementById("age-gate");
  if (localStorage.getItem("ageVerified") === "1") return;

  gate.hidden = false;
  document.getElementById("age-yes").onclick = () => {
    localStorage.setItem("ageVerified", "1");
    gate.hidden = true;
  };
  document.getElementById("age-no").onclick = () => {
    location.href = "https://www.google.com/";
  };
}

function renderSummaryCards(data) {
  const el = document.getElementById("summary-cards");
  el.innerHTML = data.regions
    .map(
      (r) => `
    <article class="card">
      <div class="card__label">${r.name}</div>
      <div class="card__value">${fmt(r.shop_count)}<span style="font-size:1rem"> 店</span></div>
      <div class="card__sub">在籍 ${fmt(r.girl_count)} 人 · 1店あたり ${r.girl_per_shop ?? "—"} 人</div>
      <div class="card__sub">相場中央値 ${fmtYen(r.price_stats?.median)}</div>
    </article>`
    )
    .join("");
}

function renderComparisonTable(data) {
  const tbody = document.querySelector("#comparison-table tbody");
  tbody.innerHTML = data.comparison
    .map(
      (r) => `
    <tr>
      <td>${r.name}</td>
      <td>${fmt(r.shop_count)}</td>
      <td>${fmt(r.girl_count)}</td>
      <td>${r.girl_per_shop ?? "—"}</td>
      <td>${fmt(r.genre_deli)}</td>
      <td>${fmt(r.genre_soap)}</td>
      <td>${fmtYen(r.median_price)}</td>
    </tr>`
    )
    .join("");
}

function makeBarChart(canvasId, labels, values, label, color) {
  const ctx = document.getElementById(canvasId);
  return new Chart(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: [{ label, data: values, backgroundColor: color, borderRadius: 8 }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        y: { beginAtZero: true, ticks: { color: "#9aa3b5" }, grid: { color: "#2a3144" } },
        x: { ticks: { color: "#9aa3b5" }, grid: { display: false } },
      },
    },
  });
}

function renderCharts(data) {
  const labels = data.comparison.map((r) => r.name);
  makeBarChart("chart-shops", labels, data.comparison.map((r) => r.shop_count), "店舗数", COLORS[0]);
  makeBarChart("chart-girls", labels, data.comparison.map((r) => r.girl_count), "在籍数", COLORS[1]);
  makeBarChart(
    "chart-price",
    labels,
    data.comparison.map((r) => r.median_price ?? 0),
    "相場中央値(円)",
    COLORS[2]
  );
}

function renderRegionSections(data) {
  const root = document.getElementById("region-sections");
  root.innerHTML = data.regions
    .map((region) => {
      const genrePills = region.genres
        .map((g) => `<span class="pill">${g.name} <strong>${fmt(g.shop_count)}</strong></span>`)
        .join("");

      const topReviews = region.top_by_reviews
        .map(
          (s) => `
        <li>
          <div>
            <a href="${s.url}" target="_blank" rel="noopener">${s.name}</a>
            <div class="shop-meta">${s.genre ?? ""}</div>
          </div>
          <div class="shop-meta">口コミ ${fmt(s.review_count)} · ${s.min_minutes ?? "?"}分 ${fmtYen(s.min_price)}</div>
        </li>`
        )
        .join("");

      const topValue = region.top_by_value
        .slice(0, 5)
        .map(
          (s) => `
        <li>
          <div>
            <a href="${s.url}" target="_blank" rel="noopener">${s.name}</a>
            <div class="shop-meta">${s.genre ?? ""}</div>
          </div>
          <div class="shop-meta">口コミ ${fmt(s.review_count)} / ${fmtYen(s.min_price)}</div>
        </li>`
        )
        .join("");

      return `
      <article class="region-block">
        <div class="region-head">
          <h2>${region.name} <span style="color:var(--muted);font-size:0.95rem">客目線サマリー</span></h2>
        </div>
        <div class="stat-pills">${genrePills}</div>
        <div class="chart-grid" style="margin-top:1rem">
          <div class="chart-box"><canvas id="genre-${region.slug}"></canvas></div>
        </div>
        <h3>口コミ件数トップ</h3>
        <ul class="shop-list">${topReviews || "<li>データなし</li>"}</ul>
        <h3>コスパ指標トップ <span style="color:var(--muted);font-size:0.85rem">口コミ数÷最低料金</span></h3>
        <ul class="shop-list">${topValue || "<li>データなし</li>"}</ul>
      </article>`;
    })
    .join("");

  data.regions.forEach((region) => {
    const ctx = document.getElementById(`genre-${region.slug}`);
    if (!ctx) return;
    new Chart(ctx, {
      type: "doughnut",
      data: {
        labels: region.genres.map((g) => g.name),
        datasets: [
          {
            data: region.genres.map((g) => g.shop_count),
            backgroundColor: COLORS,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { position: "bottom", labels: { color: "#9aa3b5" } } },
      },
    });
  });
}

async function main() {
  setupAgeGate();
  const res = await fetch("data/summary.json");
  const data = await res.json();

  document.getElementById("updated-at").textContent = `更新: ${data.updated_at ?? "—"}`;
  renderSummaryCards(data);
  renderComparisonTable(data);
  renderCharts(data);
  renderRegionSections(data);
}

main().catch((err) => {
  console.error(err);
  document.body.insertAdjacentHTML(
    "beforeend",
    `<p style="color:#ff7eb3;text-align:center">データ読み込みに失敗しました。run.py を実行してください。</p>`
  );
});
