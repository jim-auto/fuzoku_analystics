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

function fmtDelta(n, suffix = "") {
  if (n == null) return "";
  if (n === 0) return `<span class="delta delta--flat">±0${suffix}</span>`;
  const cls = n > 0 ? "delta--up" : "delta--down";
  const sign = n > 0 ? "+" : "";
  return `<span class="delta ${cls}">${sign}${fmt(n)}${suffix}</span>`;
}

function renderChanges(data) {
  const panel = document.getElementById("changes-panel");
  const changes = data.changes;
  if (!changes) {
    panel.hidden = false;
    document.getElementById("changes-desc").textContent =
      "初回スナップショットを保存しました。次回 run.py 実行後から前回比が表示されます。";
    document.getElementById("changes-content").innerHTML = "";
    return;
  }

  panel.hidden = false;
  document.getElementById("changes-desc").textContent =
    `${changes.since} から ${changes.days ?? "?"} 日間の変化`;

  const nameBySlug = Object.fromEntries((data.regions || []).map((r) => [r.slug, r.short]));
  document.getElementById("changes-content").innerHTML = `
    <div class="changes-grid">
      ${changes.regions
        .map(
          (c) => `
        <article class="change-card">
          <h3>${nameBySlug[c.slug] || c.slug}</h3>
          <div class="change-row"><span>掲載店舗</span><span>${fmtDelta(c.shop_count_delta, " 店")}</span></div>
          <div class="change-row"><span>在籍数</span><span>${fmtDelta(c.girl_count_delta, " 人")}</span></div>
          <div class="change-row"><span>相場中央値</span><span>${fmtDelta(c.median_price_delta, " 円")}</span></div>
          <div class="change-row"><span>口コミ中央値</span><span>${fmtDelta(c.median_reviews_delta, " 件")}</span></div>
          <div class="change-row"><span>デリヘル掲載</span><span>${fmtDelta(c.genre_deli_delta, " 店")}</span></div>
          ${
            (c.review_movers || []).length
              ? `<h4 style="margin:0.75rem 0 0.35rem;font-size:0.85rem;color:var(--muted)">口コミ増加トップ</h4>
                 <ul class="shop-list">${c.review_movers
                   .map(
                     (m) =>
                       `<li><div><a href="${m.url}" target="_blank" rel="noopener">${m.name}</a></div><div class="shop-meta">+${fmt(m.review_delta)} 件</div></li>`
                   )
                   .join("")}</ul>`
              : ""
          }
          ${
            (c.rank_changes || []).length
              ? `<h4 style="margin:0.75rem 0 0.35rem;font-size:0.85rem;color:var(--muted)">ランキング変動</h4>
                 <ul class="shop-list">${c.rank_changes
                   .map(
                     (m) =>
                       `<li><div><a href="${m.url}" target="_blank" rel="noopener">${m.name}</a></div><div class="shop-meta">${m.label}${m.rank_delta != null ? ` (${m.rank_delta > 0 ? "+" : ""}${m.rank_delta})` : ""}</div></li>`
                   )
                   .join("")}</ul>`
              : ""
          }
        </article>`
        )
        .join("")}
    </div>`;
}

function renderTrendCharts(trends) {
  const panel = document.getElementById("trends-panel");
  if (!trends?.dates?.length || trends.dates.length < 2) {
    return;
  }
  panel.hidden = false;

  const labels = trends.dates.map((d) => d.slice(5));
  const slugs = ["tokyo", "aichi", "osaka"];
  const names = { tokyo: "東京", aichi: "名古屋", osaka: "大阪" };

  const priceDatasets = slugs.map((slug) => ({
    label: names[slug],
    data: trends.series[slug]?.median_price || [],
    borderColor: REGION_COLORS[names[slug]],
    backgroundColor: REGION_COLORS[names[slug]] + "33",
    tension: 0.3,
    fill: false,
  }));

  const shopDatasets = slugs.map((slug) => ({
    label: names[slug],
    data: trends.series[slug]?.shop_count || [],
    borderColor: REGION_COLORS[names[slug]],
    backgroundColor: REGION_COLORS[names[slug]] + "33",
    tension: 0.3,
    fill: false,
  }));

  new Chart(document.getElementById("chart-trend-price"), {
    type: "line",
    data: { labels, datasets: priceDatasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { labels: { color: "#9aa3b5" } },
        title: { display: true, text: "相場中央値の推移", color: "#9aa3b5" },
      },
      scales: {
        y: { ticks: { color: "#9aa3b5" }, grid: { color: "#2a3144" } },
        x: { ticks: { color: "#9aa3b5" }, grid: { display: false } },
      },
    },
  });

  new Chart(document.getElementById("chart-trend-shops"), {
    type: "line",
    data: { labels, datasets: shopDatasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { labels: { color: "#9aa3b5" } },
        title: { display: true, text: "掲載店舗数の推移", color: "#9aa3b5" },
      },
      scales: {
        y: { ticks: { color: "#9aa3b5" }, grid: { color: "#2a3144" } },
        x: { ticks: { color: "#9aa3b5" }, grid: { display: false } },
      },
    },
  });
}

function renderBakusai(data) {
  const root = document.getElementById("bakusai-content");
  const bakusai = data.bakusai;
  const cross = data.bakusai_cross || [];
  if (!bakusai?.regions?.length) {
    root.innerHTML = "<p class='shop-meta'>データなし</p>";
    return;
  }

  root.innerHTML = bakusai.regions
    .map((region) => {
      const crossRegion = cross.find((c) => c.slug === region.slug) || {};
      const topThreads = (region.top_by_responses || [])
        .slice(0, 8)
        .map(
          (t) =>
            `<li><div><a href="${t.url}" target="_blank" rel="noopener">${t.title}</a><div class="shop-meta">${t.area || ""}</div></div><div class="shop-meta">レス ${fmt(t.responses)} · 閲覧 ${fmt(t.views)}</div></li>`
        )
        .join("");

      const matched = (crossRegion.matched || [])
        .map(
          (m) =>
            `<li><div>${m.name}</div><div class="shop-meta">CH ${fmt(m.heaven_reviews)} 件 / 爆サイ ${fmt(m.bakusai_responses)} レス</div></li>`
        )
        .join("");

      const areaStats = (region.area_stats || [])
        .slice(0, 5)
        .map(
          (a) =>
            `<tr><td>${a.area}</td><td>${fmt(a.thread_count)}</td><td>${fmt(a.total_responses)}</td><td>${fmt(a.median_responses)}</td></tr>`
        )
        .join("");

      return `
      <article class="region-block">
        <h3>${region.name} <a href="${region.board_url}" target="_blank" rel="noopener" style="font-size:0.8rem;color:var(--muted)">掲示板↗</a></h3>
        <div class="stat-grid">
          <div class="stat-box"><div class="stat-box__label">スレ数</div><div class="stat-box__value">${fmt(region.thread_count)}</div></div>
          <div class="stat-box"><div class="stat-box__label">総レス数</div><div class="stat-box__value">${fmt(region.total_responses)}</div></div>
          <div class="stat-box"><div class="stat-box__label">CH突合</div><div class="stat-box__value">${fmt(crossRegion.matched_count)} 店</div></div>
        </div>
        <h4>レス数トップ（話題店）</h4>
        <ul class="shop-list">${topThreads || "<li>なし</li>"}</ul>
        <h4>エリア別盛り上がり</h4>
        ${renderDataTable(["エリア", "スレ数", "総レス", "レス中央値"], areaStats)}
        ${
          matched
            ? `<h4>City Heaven × 爆サイ 一致店</h4><ul class="shop-list">${matched}</ul>`
            : ""
        }
      </article>`;
    })
    .join("");
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
  renderChanges(data);
  renderTrendCharts(data.trends);
  renderBakusai(data);
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
