(() => {
  const ALL_SIGNALS = ["강매수", "매수", "중립~매수", "중립", "관망", "매도", "회피"];

  const state = {
    search: "",
    signals: new Set(ALL_SIGNALS),
    markets: new Set(["Y", "K"]),
    sort: "time-desc",
    view: "flat",
  };

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

  const flatTbody = $("#flatTbody");
  const groupedRoot = $("#viewGrouped");
  const indexMeta = $("#indexMeta");

  // ------- Filtering -------
  function rowMatches(el) {
    const corp = el.dataset.corp || "";
    const code = el.dataset.code || "";
    if (state.search) {
      const q = state.search.toLowerCase();
      if (!corp.includes(q) && !code.includes(q)) return false;
    }
    if (state.markets.size && !state.markets.has(el.dataset.market)) return false;
    return true;
  }

  function flatRowMatches(tr) {
    if (!rowMatches(tr)) return false;
    if (state.signals.size && !state.signals.has(tr.dataset.signal)) return false;
    return true;
  }

  function groupMatches(tbody) {
    if (!rowMatches(tbody)) return false;
    if (state.signals.size) {
      const groupSignals = (tbody.dataset.groupSignals || "").split(",");
      if (!groupSignals.some((s) => state.signals.has(s))) return false;
    }
    return true;
  }

  function applyFilters() {
    let visibleFlat = 0;
    $$("#flatTbody > tr").forEach((tr) => {
      const ok = flatRowMatches(tr);
      tr.style.display = ok ? "" : "none";
      if (ok) visibleFlat++;
    });

    let visibleGroups = 0;
    let visibleGroupedRows = 0;
    $$(".stock-group", groupedRoot).forEach((tb) => {
      const ok = groupMatches(tb);
      tb.style.display = ok ? "" : "none";
      if (ok) {
        visibleGroups++;
        visibleGroupedRows += $$("tr", tb).length;
      }
    });

    if (indexMeta) {
      if (state.view === "flat") {
        const totalCorps = new Set(
          $$("#flatTbody > tr")
            .filter((tr) => tr.style.display !== "none")
            .map((tr) => tr.dataset.code || tr.dataset.corp)
        ).size;
        indexMeta.textContent = `표시 ${visibleFlat}건 · ${totalCorps}개 종목`;
      } else {
        indexMeta.textContent = `표시 ${visibleGroupedRows}건 · ${visibleGroups}개 종목`;
      }
    }
  }

  // ------- Sorting -------
  function compare(a, b, key, dir) {
    let av, bv;
    if (key === "time") {
      av = a.dataset.time || "00:00";
      bv = b.dataset.time || "00:00";
      if (av < bv) return dir === "asc" ? -1 : 1;
      if (av > bv) return dir === "asc" ? 1 : -1;
      return 0;
    }
    if (key === "signal") {
      av = parseInt(a.dataset.signalRank || "0", 10);
      bv = parseInt(b.dataset.signalRank || "0", 10);
    } else if (key === "rate") {
      av = parseFloat(a.dataset.rate || "0");
      bv = parseFloat(b.dataset.rate || "0");
    } else if (key === "cap") {
      av = parseFloat(a.dataset.cap || "0");
      bv = parseFloat(b.dataset.cap || "0");
    } else {
      return 0;
    }
    return dir === "asc" ? av - bv : bv - av;
  }

  function applySort() {
    const [key, dir] = state.sort.split("-");
    if (flatTbody) {
      const rows = $$("#flatTbody > tr");
      rows.sort((a, b) => compare(a, b, key, dir));
      const frag = document.createDocumentFragment();
      rows.forEach((r) => frag.appendChild(r));
      flatTbody.appendChild(frag);
    }
    if (groupedRoot) {
      const table = $(".disclosure-table", groupedRoot);
      const groups = $$(".stock-group", groupedRoot);
      groups.sort((a, b) => compare(a, b, key, dir));
      groups.forEach((g) => table.appendChild(g));
    }
  }

  // ------- View toggle -------
  function applyView() {
    $("#viewFlat")?.classList.toggle("hidden", state.view !== "flat");
    $("#viewGrouped")?.classList.toggle("hidden", state.view !== "grouped");
    $$(".view-btn").forEach((b) => b.classList.toggle("active", b.dataset.view === state.view));
  }

  // ------- Signal pill UI sync -------
  function syncSignalPills() {
    $$(".signal-pill[data-signal-filter]").forEach((p) => {
      p.classList.toggle("muted", !state.signals.has(p.dataset.signalFilter));
    });
  }

  function syncMarketToggles() {
    $$(".market-toggle").forEach((b) => {
      b.classList.toggle("active", state.markets.has(b.dataset.marketFilter));
    });
  }

  // ------- Event wiring -------
  $("#searchInput")?.addEventListener("input", (e) => {
    state.search = e.target.value.trim();
    applyFilters();
  });

  $$(".signal-pill[data-signal-filter]").forEach((p) => {
    p.addEventListener("click", () => {
      const sig = p.dataset.signalFilter;
      if (state.signals.has(sig)) state.signals.delete(sig);
      else state.signals.add(sig);
      // If user clicks one and all others are off, treat as "solo" toggle
      syncSignalPills();
      applyFilters();
    });
  });

  $$(".market-toggle").forEach((b) => {
    b.addEventListener("click", () => {
      const m = b.dataset.marketFilter;
      if (state.markets.has(m)) state.markets.delete(m);
      else state.markets.add(m);
      syncMarketToggles();
      applyFilters();
    });
  });

  $("#sortSelect")?.addEventListener("change", (e) => {
    state.sort = e.target.value;
    applySort();
  });

  $$(".view-btn").forEach((b) => {
    b.addEventListener("click", () => {
      state.view = b.dataset.view;
      applyView();
      applyFilters();
    });
  });

  $("#resetFilters")?.addEventListener("click", () => {
    state.search = "";
    state.signals = new Set(ALL_SIGNALS);
    state.markets = new Set(["Y", "K"]);
    state.sort = "time-desc";
    state.view = "flat";
    const si = $("#searchInput");
    if (si) si.value = "";
    const ss = $("#sortSelect");
    if (ss) ss.value = "time-desc";
    syncSignalPills();
    syncMarketToggles();
    applyView();
    applySort();
    applyFilters();
  });

  // ------- Init -------
  syncSignalPills();
  syncMarketToggles();
  applyView();
  applyFilters();
})();
