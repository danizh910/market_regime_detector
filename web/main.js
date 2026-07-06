import "./styles.css";

const app = document.querySelector("#app");
const state = {
  manifest: null,
  activeRunId: null,
  activeTab: "stats",
  tables: new Map(),
};

const regimeClass = (name = "") => {
  const lower = name.toLowerCase();
  if (lower.includes("stress")) return "stress";
  if (lower.includes("bear") || lower.includes("drawdown")) return "bear";
  if (lower.includes("high-vol")) return "volatile";
  if (lower.includes("bull") || lower.includes("recovery")) return "bull";
  return "mixed";
};

const formatPercent = (value, digits = 1) => {
  const number = Number(value);
  if (!Number.isFinite(number)) return "n/a";
  return `${(number * 100).toFixed(digits)}%`;
};

const formatNumber = (value, digits = 0) => {
  const number = Number(value);
  if (!Number.isFinite(number)) return "n/a";
  return number.toLocaleString("en-US", { maximumFractionDigits: digits });
};

const parseCsv = (text) => {
  const lines = text.trim().split(/\r?\n/);
  const headers = lines.shift().split(",");
  return lines.map((line) => {
    const values = [];
    let current = "";
    let quoted = false;
    for (const char of line) {
      if (char === '"') {
        quoted = !quoted;
      } else if (char === "," && !quoted) {
        values.push(current);
        current = "";
      } else {
        current += char;
      }
    }
    values.push(current);
    return Object.fromEntries(headers.map((header, index) => [header, values[index] ?? ""]));
  });
};

const loadTable = async (path) => {
  if (state.tables.has(path)) return state.tables.get(path);
  const response = await fetch(path);
  if (!response.ok) throw new Error(`Could not load ${path}`);
  const rows = parseCsv(await response.text());
  state.tables.set(path, rows);
  return rows;
};

const availableFilters = () => {
  const runs = state.manifest.runs;
  return {
    regions: ["All", ...new Set(runs.map((run) => run.region))].sort((a, b) =>
      a === "All" ? -1 : a.localeCompare(b),
    ),
    assetClasses: ["All", ...new Set(runs.map((run) => run.assetClass))],
    timeframes: [...new Set(runs.map((run) => run.timeframe))],
  };
};

const activeRun = () =>
  state.manifest.runs.find((run) => run.id === state.activeRunId) ?? state.manifest.runs[0];

const setActiveRun = async (runId) => {
  state.activeRunId = runId;
  await render();
};

const setActiveTab = async (tab) => {
  state.activeTab = tab;
  await render();
};

const tableView = (rows, columns) => `
  <div class="table-wrap">
    <table>
      <thead>
        <tr>${columns.map((column) => `<th>${column.label}</th>`).join("")}</tr>
      </thead>
      <tbody>
        ${rows
          .map(
            (row) => `
              <tr>
                ${columns
                  .map((column) => `<td>${column.format ? column.format(row[column.key], row) : row[column.key]}</td>`)
                  .join("")}
              </tr>
            `,
          )
          .join("")}
      </tbody>
    </table>
  </div>
`;

const renderTabs = async (run) => {
  const tabs = [
    ["stats", "Regime statistics"],
    ["transitions", "Transitions"],
    ["strategy", "Strategy diagnostic"],
    ["model", "Model selection"],
  ];

  let body = "";
  if (state.activeTab === "stats") {
    const rows = await loadTable(run.paths.regimeStats);
    body = tableView(rows, [
      { key: "regime_name", label: "Regime" },
      { key: "frequency_pct", label: "Frequency", format: formatPercent },
      { key: "annualized_return", label: "Ann. return", format: formatPercent },
      { key: "annualized_volatility", label: "Ann. volatility", format: formatPercent },
      { key: "avg_duration_days", label: "Avg. duration", format: (value) => `${formatNumber(value, 1)} bars` },
      { key: "avg_drawdown", label: "Avg. drawdown", format: formatPercent },
    ]);
  }

  if (state.activeTab === "transitions") {
    body = `
      <div class="split-media">
        <img src="${run.paths.transitionChart}" alt="Transition matrix for ${run.symbol}" />
        <div>
          <h3>Why it matters</h3>
          <p>
            An HMM estimates not only the regime today, but also the probability of
            staying in or moving to another regime. High diagonal probabilities mean
            the state is persistent rather than just a one-bar classification.
          </p>
        </div>
      </div>
    `;
  }

  if (state.activeTab === "strategy") {
    const rows = await loadTable(run.paths.strategy);
    body = `
      <div class="split-media">
        <img src="${run.paths.strategyChart}" alt="Strategy by regime for ${run.symbol}" />
        ${tableView(rows, [
          { key: "regime_name", label: "Regime" },
          { key: "buy_hold_ann_return", label: "Buy & hold", format: formatPercent },
          { key: "trend_ann_return", label: "Trend rule", format: formatPercent },
          { key: "trend_exposure_pct", label: "Exposure", format: formatPercent },
        ])}
      </div>
    `;
  }

  if (state.activeTab === "model") {
    const rows = await loadTable(run.paths.modelSelection);
    body = `
      <div class="split-media">
        <img src="${run.paths.modelSelectionChart}" alt="Model selection for ${run.symbol}" />
        ${tableView(rows, [
          { key: "n_states", label: "States" },
          { key: "log_likelihood", label: "Log likelihood", format: (value) => formatNumber(value, 1) },
          { key: "aic", label: "AIC", format: (value) => formatNumber(value, 0) },
          { key: "bic", label: "BIC", format: (value) => formatNumber(value, 0) },
        ])}
      </div>
    `;
  }

  return `
    <section class="panel">
      <div class="tabs">
        ${tabs
          .map(
            ([id, label]) => `
              <button class="tab ${state.activeTab === id ? "active" : ""}" data-tab="${id}">
                ${label}
              </button>
            `,
          )
          .join("")}
      </div>
      <div class="tab-body">${body}</div>
    </section>
  `;
};

const renderSnapshot = (runs) => `
  <section class="panel">
    <div class="section-heading">
      <div>
        <p class="eyebrow">Cross-market snapshot</p>
        <h2>Latest detected regimes</h2>
      </div>
      <span>${runs.length} generated model runs</span>
    </div>
    <div class="snapshot-grid">
      ${runs
        .map(
          (run) => `
            <button class="snapshot-card ${run.id === state.activeRunId ? "selected" : ""}" data-run="${run.id}">
              <span>${run.assetName}</span>
              <strong>${run.symbol}</strong>
              <small>${run.timeframeLabel}</small>
              <mark class="${regimeClass(run.latest?.regimeName)}">${run.latest?.regimeName ?? "No latest label"}</mark>
            </button>
          `,
        )
        .join("")}
    </div>
  </section>
`;

const render = async () => {
  const run = activeRun();
  const runs = state.manifest.runs;
  const filters = availableFilters();
  const grouped = runs.reduce((acc, item) => {
    acc[item.region] = (acc[item.region] ?? 0) + 1;
    return acc;
  }, {});

  app.innerHTML = `
    <main>
      <aside class="sidebar">
        <div class="brand">
          <span class="brand-mark">MR</span>
          <div>
            <strong>Market Regime</strong>
            <small>HMM Dashboard</small>
          </div>
        </div>
        <label>
          Instrument
          <select id="run-select">
            ${runs
              .map(
                (item) => `
                  <option value="${item.id}" ${item.id === run.id ? "selected" : ""}>
                    ${item.symbol} · ${item.timeframe}
                  </option>
                `,
              )
              .join("")}
          </select>
        </label>
        <div class="filter-list">
          <span>Coverage</span>
          ${filters.regions
            .filter((region) => region !== "All")
            .map((region) => `<p><strong>${region}</strong><small>${grouped[region] ?? 0} runs</small></p>`)
            .join("")}
        </div>
        <div class="note">
          <strong>Deployment model</strong>
          <p>Vercel hosts this static dashboard. Python generates the HMM artifacts before deployment.</p>
        </div>
      </aside>

      <section class="content">
        <header class="hero">
          <div>
            <p class="eyebrow">Unsupervised regime detection</p>
            <h1>${run.assetName}</h1>
            <p>
              ${run.description}. Current view: ${run.region}, ${run.assetClass},
              ${run.timeframeLabel.toLowerCase()} bars.
            </p>
          </div>
          <div class="hero-metrics">
            <article>
              <span>Latest regime</span>
              <strong class="${regimeClass(run.latest?.regimeName)}">${run.latest?.regimeName ?? "n/a"}</strong>
            </article>
            <article>
              <span>Selected states</span>
              <strong>${run.bestModel.states}</strong>
            </article>
            <article>
              <span>Annualized vol</span>
              <strong>${formatPercent(run.latest?.annualizedVolatility)}</strong>
            </article>
          </div>
        </header>

        <section class="chart-panel">
          <img src="${run.paths.priceChart}" alt="Price chart with detected regimes for ${run.symbol}" />
        </section>

        <section class="metric-grid">
          <article>
            <span>Annualized return in latest regime</span>
            <strong>${formatPercent(run.latest?.annualizedReturn)}</strong>
          </article>
          <article>
            <span>Latest regime frequency</span>
            <strong>${formatPercent(run.latest?.frequency)}</strong>
          </article>
          <article>
            <span>Best BIC</span>
            <strong>${formatNumber(run.bestModel.bic)}</strong>
          </article>
          <article>
            <span>Last label date</span>
            <strong>${run.latest?.date?.slice(0, 10) ?? "n/a"}</strong>
          </article>
        </section>

        ${await renderTabs(run)}
        ${renderSnapshot(runs)}

        <footer>
          Educational project only. The full-sample HMM labels are explanatory and include look-ahead bias.
          Generated ${state.manifest.generatedAt}.
        </footer>
      </section>
    </main>
  `;

  document.querySelector("#run-select").addEventListener("change", (event) => {
    setActiveRun(event.target.value);
  });
  document.querySelectorAll("[data-run]").forEach((button) => {
    button.addEventListener("click", () => setActiveRun(button.dataset.run));
  });
  document.querySelectorAll("[data-tab]").forEach((button) => {
    button.addEventListener("click", () => setActiveTab(button.dataset.tab));
  });
};

const bootstrap = async () => {
  const response = await fetch("/manifest.json");
  state.manifest = await response.json();
  state.activeRunId = state.manifest.runs.find((run) => run.id === "BTC-USD_1d")?.id ?? state.manifest.runs[0].id;
  await render();
};

bootstrap().catch((error) => {
  app.innerHTML = `<main class="error"><h1>Dashboard failed to load</h1><p>${error.message}</p></main>`;
});
