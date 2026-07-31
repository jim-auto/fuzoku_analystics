const COLORS = ["#6c8cff", "#ff7eb3", "#4ade80", "#fbbf24", "#a78bfa"];
const REGION_COLORS = { 東京: COLORS[0], 名古屋: COLORS[1], 大阪: COLORS[2] };

function fmt(n) {
  if (n == null) return "—";
  return n.toLocaleString("ja-JP");
}

function fmtYen(n) {
  if (n == null) return "—";
  return `${n.toLocaleString("ja-JP")}円`;
}

function fmtPct(n) {
  if (n == null) return "—";
  return `${n}%`;
}

function isAgeVerified() {
  try {
    return localStorage.getItem("ageVerified") === "1" || sessionStorage.getItem("ageVerified") === "1";
  } catch {
    return false;
  }
}

function markAgeVerified() {
  try {
    localStorage.setItem("ageVerified", "1");
  } catch {
    try {
      sessionStorage.setItem("ageVerified", "1");
    } catch {
      /* noop */
    }
  }
}

function closeAgeGate() {
  const gate = document.getElementById("age-gate");
  gate.classList.remove("is-open");
  gate.setAttribute("aria-hidden", "true");
}

function setupAgeGate() {
  const gate = document.getElementById("age-gate");
  const yesBtn = document.getElementById("age-yes");
  const noBtn = document.getElementById("age-no");

  if (isAgeVerified()) {
    closeAgeGate();
    return;
  }

  gate.classList.add("is-open");
  gate.setAttribute("aria-hidden", "false");

  yesBtn.addEventListener("click", (e) => {
    e.preventDefault();
    markAgeVerified();
    closeAgeGate();
  });

  noBtn.addEventListener("click", (e) => {
    e.preventDefault();
    location.href = "https://www.google.com/";
  });
}

function renderMetroInsights(data) {
  const el = document.getElementById("metro-insights");
  const overview = data.metro_overview || {};
  const ps = overview.metro_price_stats || {};
  el.innerHTML = `
    <h2>分析サマリー（東名阪）</h2>
    <div class="stat-grid">
      <div class="stat-box"><div class="stat-box__label">3都市 掲載店舗</div><div class="stat-box__value">${fmt(overview.total_official_shops)} 店</div></div>
      <div class="stat-box"><div class="stat-box__label">分析サンプル</div><div class="stat-box__value">${fmt(overview.total_sampled_shops)} 店</div></div>
      <div class="stat-box"><div class="stat-box__label">相場中央値</div><div class="stat-box__value">${fmtYen(ps.median)}</div></div>
      <div class="stat-box"><div class="stat-box__label">相場平均</div><div class="stat-box__value">${fmtYen(ps.mean)}</div></div>
      <div class="stat-box"><div class="stat-box__label">四分位 (P25–P75)</div><div class="stat-box__value">${fmtYen(ps.p25)} – ${fmtYen(ps.p75)}</div></div>
      <div class="stat-box"><div class="stat-box__label">標準偏差</div><div class="stat-box__value">${fmtYen(ps.stdev)}</div></div>
    </div>
    <ul class="insights-list">${(overview.insights || []).map((t) => `<li>${t}</li>`).join("")}</ul>
  `;
}

function renderSummaryCards(data) {
  const el = document.getElementById("summary-cards");
  el.innerHTML = data.regions
    .map((r) => {
      const ps = r.price_stats || {};
      const rs = r.review_stats || {};
      return `
    <article class="card">
      <div class="card__label">${r.name}</div>
      <div class="card__value">${fmt(r.shop_count)}<span style="font-size:1rem"> 店</span></div>
      <div class="card__sub">分析 ${fmt(r.coverage?.sampled)} 店 (${fmtPct(r.coverage?.pct)})</div>
      <div class="card__sub">相場 P50 ${fmtYen(ps.median)} / P25–P75 ${fmtYen(ps.p25)}–${fmtYen(ps.p75)}</div>
      <div class="card__sub">口コミ中央値 ${fmt(rs.median)} 件 · 1分 ${fmtYen(r.price_per_minute_stats?.median)}</div>
    </article>`;
    })
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
      <td>${fmtPct(r.coverage_pct)}</td>
      <td>${r.girl_per_shop ?? "—"}</td>
      <td>${fmtYen(r.median_price)}</td>
      <td>${fmtYen(r.median_ppm)}</td>
      <td>${fmt(r.median_reviews)}</td>
      <td>${fmtPct(r.top5_review_share)}</td>
    </tr>`
    )
    .join("");
}

function makeBarChart(canvasId, labels, datasets, options = {}) {
  const ctx = document.getElementById(canvasId);
  return new Chart(ctx, {
    type: "bar",
    data: { labels, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: datasets.length > 1, labels: { color: "#9aa3b5" } } },
      scales: {
        y: { beginAtZero: true, ticks: { color: "#9aa3b5" }, grid: { color: "#2a3144" } },
        x: { ticks: { color: "#9aa3b5" }, grid: { display: false } },
      },
      ...options,
    },
  });
}

function renderCharts(data) {
  const labels = data.comparison.map((r) => r.name);
  makeBarChart("chart-shops", labels, [
    { label: "店舗数", data: data.comparison.map((r) => r.shop_count), backgroundColor: COLORS[0], borderRadius: 8 },
  ]);
  makeBarChart("chart-girls", labels, [
    { label: "在籍/店", data: data.comparison.map((r) => r.girl_per_shop ?? 0), backgroundColor: COLORS[1], borderRadius: 8 },
  ]);
  makeBarChart("chart-price", labels, [
    { label: "相場中央値", data: data.comparison.map((r) => r.median_price ?? 0), backgroundColor: COLORS[2], borderRadius: 8 },
  ]);
  makeBarChart("chart-ppm", labels, [
    { label: "1分単価中央値", data: data.comparison.map((r) => r.median_ppm ?? 0), backgroundColor: COLORS[4], borderRadius: 8 },
  ]);
}

function renderMetroHistograms(data) {
  const bucketLabels = data.regions[0]?.price_histogram?.map((b) => b.label) || [];
  makeBarChart(
    "chart-price-hist",
    bucketLabels,
    data.regions.map((r) => ({
      label: r.short,
      data: (r.price_histogram || []).map((b) => b.pct),
      backgroundColor: REGION_COLORS[r.short] || COLORS[0],
      borderRadius: 6,
    })),
    {
      plugins: {
        legend: { display: true, labels: { color: "#9aa3b5" } },
        title: { display: true, text: "最低コース料金の分布 (%)", color: "#9aa3b5" },
      },
    }
  );

  const reviewLabels = data.regions[0]?.review_histogram?.map((b) => b.label) || [];
  makeBarChart(
    "chart-review-hist",
    reviewLabels,
    data.regions.map((r) => ({
      label: r.short,
      data: (r.review_histogram || []).map((b) => b.pct),
      backgroundColor: REGION_COLORS[r.short] || COLORS[0],
      borderRadius: 6,
    })),
    {
      plugins: {
        legend: { display: true, labels: { color: "#9aa3b5" } },
        title: { display: true, text: "口コミ件数の分布 (%)", color: "#9aa3b5" },
      },
    }
  );
}

function statBoxes(title, stats, fields) {
  return `
    <h3>${title}</h3>
    <div class="stat-grid">
      ${fields
        .map(
          ([label, key, fmtFn]) =>
            `<div class="stat-box"><div class="stat-box__label">${label}</div><div class="stat-box__value">${(fmtFn || fmt)(stats?.[key])}</div></div>`
        )
        .join("")}
    </div>`;
}

function renderDataTable(headers, rows) {
  if (!rows.length) return "<p class='shop-meta'>データなし</p>";
  return `
    <div class="table-wrap">
      <table class="data-table">
        <thead><tr>${headers.map((h) => `<th>${h}</th>`).join("")}</tr></thead>
        <tbody>${rows.join("")}</tbody>
      </table>
    </div>`;
}

function renderRegionSections(data) {
  const root = document.getElementById("region-sections");
  root.innerHTML = data.regions
    .map((region) => {
      const topReviews = (region.top_by_reviews || [])
        .map(
          (s) => `
        <li>
          <div><a href="${s.url}" target="_blank" rel="noopener">${s.name}</a><div class="shop-meta">${s.genre ?? ""}</div></div>
          <div class="shop-meta">口コミ ${fmt(s.review_count)} · ${s.min_minutes ?? "?"}分 ${fmtYen(s.min_price)}</div>
        </li>`
        )
        .join("");

      const topValue = (region.top_by_value || [])
        .slice(0, 5)
        .map(
          (s) => `
        <li>
          <div><a href="${s.url}" target="_blank" rel="noopener">${s.name}</a><div class="shop-meta">${s.genre ?? ""}</div></div>
          <div class="shop-meta">口コミ ${fmt(s.review_count)} / ${fmtYen(s.min_price)} / ${fmtYen(s.price_per_minute)}/分</div>
        </li>`
        )
        .join("");

      const genreRows = (region.genre_analysis || []).map(
        (g) =>
          `<tr><td>${g.name}</td><td>${fmt(g.sampled_count)}</td><td>${fmtPct(g.sample_pct)}</td><td>${fmtYen(g.median_price)}</td><td>${fmt(g.median_reviews)}</td><td>${fmtYen(g.median_ppm)}</td></tr>`
      );

      const areaRows = (region.area_analysis || []).map(
        (a) =>
          `<tr><td>${a.name}</td><td>${fmt(a.count)}</td><td>${fmtPct(a.pct)}</td><td>${fmtYen(a.median_price)}</td><td>${fmt(a.median_reviews)}</td></tr>`
      );

      const subgenreRows = (region.subgenre_analysis || []).map(
        (s) =>
          `<tr><td>${s.name}</td><td>${fmt(s.count)}</td><td>${fmtPct(s.pct)}</td><td>${fmtYen(s.median_price)}</td></tr>`
      );

      const mc = region.market_concentration || {};

      return `
      <article class="region-block">
        <div class="region-head">
          <h2>${region.name} <span style="color:var(--muted);font-size:0.95rem">統計詳細</span></h2>
        </div>
        <ul class="insights-list">${(region.insights || []).map((t) => `<li>${t}</li>`).join("")}</ul>

        ${statBoxes("相場統計", region.price_stats, [
          ["サンプル数", "count"],
          ["中央値 (P50)", "median", fmtYen],
          ["平均", "mean", fmtYen],
          ["P25", "p25", fmtYen],
          ["P75", "p75", fmtYen],
          ["標準偏差", "stdev", fmtYen],
        ])}

        ${statBoxes("口コミ統計", region.review_stats, [
          ["サンプル数", "count"],
          ["中央値", "median"],
          ["平均", "mean"],
          ["P25", "p25"],
          ["P75", "p75"],
          ["最大", "max"],
        ])}

        <div class="stat-grid">
          <div class="stat-box"><div class="stat-box__label">1分単価 中央値</div><div class="stat-box__value">${fmtYen(region.price_per_minute_stats?.median)}</div></div>
          <div class="stat-box"><div class="stat-box__label">口コミ 上位5店シェア</div><div class="stat-box__value">${fmtPct(mc.top5_share_pct)}</div></div>
          <div class="stat-box"><div class="stat-box__label">口コミ 上位10店シェア</div><div class="stat-box__value">${fmtPct(mc.top10_share_pct)}</div></div>
          <div class="stat-box"><div class="stat-box__label">口コミ合計</div><div class="stat-box__value">${fmt(mc.total_reviews)} 件</div></div>
        </div>

        <div class="chart-grid">
          <div class="chart-box"><canvas id="genre-${region.slug}"></canvas></div>
          <div class="chart-box"><canvas id="price-hist-${region.slug}"></canvas></div>
        </div>

        <h3>業種別統計</h3>
        ${renderDataTable(
          ["業種", "サンプル", "構成比", "相場中央値", "口コミ中央値", "1分単価"],
          genreRows
        )}

        <h3>エリア別統計（上位）</h3>
        ${renderDataTable(["エリア", "店舗数", "構成比", "相場中央値", "口コミ中央値"], areaRows)}

        <h3>コンセプト別（上位）</h3>
        ${renderDataTable(["コンセプト", "店舗数", "構成比", "相場中央値"], subgenreRows)}

        <h3>口コミ件数トップ</h3>
        <ul class="shop-list">${topReviews || "<li>データなし</li>"}</ul>

        <h3>コスパ指標トップ <span style="color:var(--muted);font-size:0.85rem">口コミ数÷最低料金</span></h3>
        <ul class="shop-list">${topValue || "<li>データなし</li>"}</ul>
      </article>`;
    })
    .join("");

  data.regions.forEach((region) => {
    const genreCtx = document.getElementById(`genre-${region.slug}`);
    if (genreCtx) {
      new Chart(genreCtx, {
        type: "doughnut",
        data: {
          labels: (region.genre_analysis || []).map((g) => g.name),
          datasets: [
            {
              data: (region.genre_analysis || []).map((g) => g.sampled_count),
              backgroundColor: COLORS,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { position: "bottom", labels: { color: "#9aa3b5" } },
            title: { display: true, text: "業種構成（サンプル）", color: "#9aa3b5" },
          },
        },
      });
    }

    const priceCtx = document.getElementById(`price-hist-${region.slug}`);
    if (priceCtx) {
      new Chart(priceCtx, {
        type: "bar",
        data: {
          labels: (region.price_histogram || []).map((b) => b.label),
          datasets: [
            {
              label: "店舗構成比 (%)",
              data: (region.price_histogram || []).map((b) => b.pct),
              backgroundColor: COLORS[0],
              borderRadius: 6,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false },
            title: { display: true, text: "料金帯分布", color: "#9aa3b5" },
          },
          scales: {
            y: { beginAtZero: true, ticks: { color: "#9aa3b5" }, grid: { color: "#2a3144" } },
            x: { ticks: { color: "#9aa3b5" }, grid: { display: false } },
          },
        },
      });
    }
  });
}

setupAgeGate();

async function main() {
  const res = await fetch(new URL("data/summary.json", document.baseURI).href);
  const data = await res.json();

  document.getElementById("updated-at").textContent = `更新: ${data.updated_at ?? "—"}`;
  renderMetroInsights(data);
  renderSummaryCards(data);
  renderComparisonTable(data);
  renderCharts(data);
  renderMetroHistograms(data);
  renderRegionSections(data);
}

main().catch((err) => {
  console.error(err);
  document.body.insertAdjacentHTML(
    "beforeend",
    `<p style="color:#ff7eb3;text-align:center">データ読み込みに失敗しました。run.py を実行してください。</p>`
  );
});
