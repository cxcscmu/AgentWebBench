/* =========================================================================
   AgentWebBench — interactions
   ========================================================================= */
(function () {
  "use strict";
  const $  = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  const D  = window.AWB;

  /* ---------------- Theme ---------------- */
  const root = document.documentElement;
  const saved = localStorage.getItem("awb-theme");
  if (saved) root.setAttribute("data-theme", saved);
  else if (window.matchMedia && matchMedia("(prefers-color-scheme: dark)").matches)
    root.setAttribute("data-theme", "dark");

  const themeBtn = $("#themeToggle");
  function syncTheme() {
    const dark = root.getAttribute("data-theme") === "dark";
    themeBtn.setAttribute("aria-pressed", String(dark));
    themeBtn.setAttribute("aria-label", dark ? "Switch to light theme" : "Switch to dark theme");
  }
  syncTheme();
  themeBtn.addEventListener("click", () => {
    const next = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
    root.setAttribute("data-theme", next);
    localStorage.setItem("awb-theme", next);
    syncTheme();
  });

  /* ---------------- Nav: scroll state, active link, burger ---------------- */
  const nav = $("#nav");
  const onScroll = () => nav.classList.toggle("is-scrolled", window.scrollY > 8);
  onScroll();
  window.addEventListener("scroll", onScroll, { passive: true });

  const burger = $("#navBurger"), links = $(".nav__links");
  burger.addEventListener("click", () => links.classList.toggle("open"));
  $$(".nav__links a").forEach(a => a.addEventListener("click", () => links.classList.remove("open")));

  // Active nav across the multi-page site: highlight the current page, and refine
  // by in-page section while scrolling (e.g. Findings on the Leaderboard page).
  const here = (location.pathname.split("/").pop() || "index.html");
  const navAnchors = $$(".nav__links a");
  const splitHref = a => a.getAttribute("href").split("#");
  const pageLink = navAnchors.find(a => { const [p, h] = splitHref(a); return !h && (p === "" || p === here); });
  const setActive = el => { if (el) navAnchors.forEach(a => a.classList.toggle("active", a === el)); };
  setActive(pageLink);
  const linkForSection = id => {
    const a = navAnchors.find(x => { const [p, h] = splitHref(x); return h === id && (p === "" || p === here); });
    return a || pageLink;
  };
  const navSections = $$("main section[id]");
  if (navSections.length) {
    const spy = new IntersectionObserver(entries => {
      entries.forEach(e => { if (e.isIntersecting) setActive(linkForSection(e.target.id)); });
    }, { rootMargin: "-45% 0px -50% 0px" });
    navSections.forEach(s => spy.observe(s));
  }

  /* ---------------- Reveal on scroll ---------------- */
  const revealIO = new IntersectionObserver(entries => {
    entries.forEach(e => { if (e.isIntersecting) { e.target.classList.add("in"); revealIO.unobserve(e.target); } });
  }, { threshold: 0.12 });
  $$(".reveal").forEach(el => revealIO.observe(el));

  /* ---------------- Animated stat counters ---------------- */
  function animateCount(el) {
    const target = parseFloat(el.dataset.count);
    const suffix = el.dataset.suffix || "";
    const isInt = Number.isInteger(target);
    const dur = 1300, start = performance.now();
    function tick(now) {
      const p = Math.min(1, (now - start) / dur);
      const eased = 1 - Math.pow(1 - p, 3);
      const val = target * eased;
      el.textContent = (isInt ? Math.round(val) : val.toFixed(1)) + suffix;
      if (p < 1) requestAnimationFrame(tick);
      else el.textContent = (isInt ? target : target.toFixed(1)) + suffix;
    }
    requestAnimationFrame(tick);
  }
  const countIO = new IntersectionObserver(entries => {
    entries.forEach(e => { if (e.isIntersecting) { animateCount(e.target); countIO.unobserve(e.target); } });
  }, { threshold: 0.6 });
  $$(".hero__stats dt").forEach(el => countIO.observe(el));

  /* ---------------- Hero canvas: agent network ---------------- */
  (function heroNet() {
    const cv = $("#heroCanvas");
    if (!cv || matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const ctx = cv.getContext("2d");
    let w, h, dpr, nodes = [], raf;
    const COUNT = () => Math.min(64, Math.round(window.innerWidth / 24));
    const mouse = { x: null, y: null };
    const LINK = 130, REACH = 200;   // node-node link distance; cursor reach

    function brand() {
      return getComputedStyle(root).getPropertyValue("--brand-rgb").trim() || "79,70,229";
    }
    function resize() {
      dpr = Math.min(2, window.devicePixelRatio || 1);
      w = cv.clientWidth; h = cv.clientHeight;
      cv.width = w * dpr; cv.height = h * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }
    function init() {
      resize();
      nodes = Array.from({ length: COUNT() }, () => ({
        x: Math.random() * w, y: Math.random() * h,
        vx: (Math.random() - .5) * .25, vy: (Math.random() - .5) * .25,
        r: Math.random() * 1.6 + 1, hub: Math.random() < .12,
      }));
    }
    function frame() {
      const rgb = brand();
      ctx.clearRect(0, 0, w, h);
      // move — with a gentle pull toward the cursor when it is near
      for (const a of nodes) {
        if (mouse.x != null) {
          const dx = mouse.x - a.x, dy = mouse.y - a.y, d = Math.hypot(dx, dy);
          if (d > 1 && d < REACH) { const f = (1 - d / REACH) * 0.04; a.vx += (dx / d) * f; a.vy += (dy / d) * f; }
        }
        a.vx *= 0.99; a.vy *= 0.99;                                   // friction
        const sp = Math.hypot(a.vx, a.vy); if (sp > 0.9) { a.vx = a.vx / sp * 0.9; a.vy = a.vy / sp * 0.9; }
        a.x += a.vx; a.y += a.vy;
        if (a.x < 0 || a.x > w) a.vx *= -1;
        if (a.y < 0 || a.y > h) a.vy *= -1;
        a.x = Math.max(0, Math.min(w, a.x)); a.y = Math.max(0, Math.min(h, a.y));
      }
      // node-to-node links
      for (let i = 0; i < nodes.length; i++) {
        const a = nodes[i];
        for (let j = i + 1; j < nodes.length; j++) {
          const b = nodes[j], dx = a.x - b.x, dy = a.y - b.y, d = Math.hypot(dx, dy);
          if (d < LINK) {
            ctx.strokeStyle = `rgba(${rgb},${(1 - d / LINK) * .18})`;
            ctx.lineWidth = 1;
            ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
          }
        }
      }
      // cursor links + glowing pointer node
      if (mouse.x != null) {
        for (const n of nodes) {
          const dx = n.x - mouse.x, dy = n.y - mouse.y, d = Math.hypot(dx, dy);
          if (d < REACH) {
            ctx.strokeStyle = `rgba(245,158,11,${(1 - d / REACH) * .5})`;
            ctx.lineWidth = 1.1;
            ctx.beginPath(); ctx.moveTo(n.x, n.y); ctx.lineTo(mouse.x, mouse.y); ctx.stroke();
          }
        }
        ctx.beginPath(); ctx.arc(mouse.x, mouse.y, 3.4, 0, Math.PI * 2);
        ctx.fillStyle = "rgba(245,158,11,.9)"; ctx.fill();
      }
      // nodes
      for (const n of nodes) {
        ctx.beginPath();
        ctx.arc(n.x, n.y, n.hub ? n.r + 1.4 : n.r, 0, Math.PI * 2);
        ctx.fillStyle = n.hub ? `rgba(245,158,11,.85)` : `rgba(${rgb},.55)`;
        ctx.fill();
      }
      raf = requestAnimationFrame(frame);
    }
    init(); frame();
    const hero = cv.parentElement;
    const setMouse = (cx, cy) => { const r = cv.getBoundingClientRect(); mouse.x = cx - r.left; mouse.y = cy - r.top; };
    hero.addEventListener("pointermove", e => setMouse(e.clientX, e.clientY));
    hero.addEventListener("pointerleave", () => { mouse.x = mouse.y = null; });
    let t; window.addEventListener("resize", () => { clearTimeout(t); t = setTimeout(() => { cancelAnimationFrame(raf); init(); frame(); }, 200); });
  })();

  /* ---------------- Task cards ---------------- */
  const TASK_ICONS = {
    search:   '<path fill="currentColor" d="M21 20l-5.6-5.6a7 7 0 1 0-1.4 1.4L20 21l1-1zM5 10a5 5 0 1 1 10 0 5 5 0 0 1-10 0z"/>',
    rec:      '<path fill="currentColor" d="M12 2l2.4 6.9H22l-6 4.3 2.3 7L12 16l-6.3 4.2 2.3-7-6-4.3h7.6L12 2z"/>',
    qa:       '<path fill="currentColor" d="M4 4h16a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H8l-4 4V6a2 2 0 0 1 2-2zm6 4a2.5 2.5 0 0 0-2.5 2.5h2A.5.5 0 1 1 12 12c-.6.3-1 .9-1 1.6V14h2v-.2c0-.3.2-.5.6-.8.8-.4 1.4-1.1 1.4-2A2.5 2.5 0 0 0 10 8z"/>',
    research: '<path fill="currentColor" d="M9 2h6a1 1 0 0 1 1 1v4l4 9.5A3 3 0 0 1 17.2 21H6.8A3 3 0 0 1 4 16.5L8 7V3a1 1 0 0 1 1-1zm1 2v3.4L6.6 16h10.8L14 7.4V4h-4z"/>',
  };
  function renderTaskCards() {
    const box = $("#taskCards");
    box.innerHTML = Object.entries(D.tasks).map(([id, t]) => `
      <article class="taskcard">
        <div class="taskcard__icon"><svg viewBox="0 0 24 24" width="22" height="22">${TASK_ICONS[t.icon]}</svg></div>
        <h4>${t.name}</h4>
        <p>${t.blurb}</p>
        <div class="taskcard__meta">
          <div class="taskcard__row"><span>Samples</span><span>${t.samples}</span></div>
          <div class="taskcard__row"><span>Output</span><span>${t.output}</span></div>
          <div class="taskcard__metrics">${t.metrics.map(m => `<b>${m.label}${m.lower ? " ↓" : ""}</b>`).join("")}</div>
        </div>
      </article>`).join("");
  }

  /* ---------------- Leaderboard ---------------- */
  const LB = {
    task: "search",
    methods: new Set(["multi"]),   // default view: Multi-Agent only (toggle others via chips)
    classicIR: false,
    search: "",
    sortKey: null,    // metric key
    sortDir: null,    // 'asc' | 'desc'
  };
  const modelById = Object.fromEntries(D.models.map(m => [m.id, m]));
  const methodById = Object.fromEntries(D.methods.map(m => [m.id, m]));

  function buildTaskTabs() {
    const box = $("#lbTasks");
    box.innerHTML = Object.entries(D.tasks).map(([id, t]) => {
      const active = id === LB.task;
      return `
      <button class="lb__tab ${active ? "active" : ""}" data-task="${id}" id="tab-${id}" role="tab"
        aria-selected="${active}" aria-controls="lbPanel" tabindex="${active ? "0" : "-1"}">
        <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">${TASK_ICONS[t.icon]}</svg>
        ${t.name} <span class="cnt">${t.samples}</span>
      </button>`;
    }).join("");
    $$("#lbTasks .lb__tab").forEach(b => b.addEventListener("click", () => selectTask(b.dataset.task, false)));
  }
  function selectTask(id, focusTab) {
    LB.task = id; LB.sortKey = null; LB.sortDir = null;
    buildTaskTabs(); render();
    if (focusTab) { const el = $(`#tab-${id}`); if (el) el.focus(); }
  }
  function onTabKey(e) {
    const ids = Object.keys(D.tasks);
    const cur = ids.indexOf(LB.task);
    let next = null;
    if (e.key === "ArrowRight" || e.key === "ArrowDown") next = (cur + 1) % ids.length;
    else if (e.key === "ArrowLeft" || e.key === "ArrowUp") next = (cur - 1 + ids.length) % ids.length;
    else if (e.key === "Home") next = 0;
    else if (e.key === "End") next = ids.length - 1;
    if (next != null) { e.preventDefault(); selectTask(ids[next], true); }
  }

  function buildMethodFilters() {
    const box = $("#lbMethodFilters");
    box.innerHTML = D.methods.map(m => {
      const on = LB.methods.has(m.id);
      return `<button type="button" class="lb__chip ${on ? "on" : ""}" data-m="${m.id}" aria-pressed="${on}">${m.short}</button>`;
    }).join("");
    $$("#lbMethodFilters .lb__chip").forEach(c => c.addEventListener("click", () => {
      const id = c.dataset.m;
      if (LB.methods.has(id)) { if (LB.methods.size > 1) LB.methods.delete(id); }
      else LB.methods.add(id);
      buildMethodFilters(); render();
    }));
  }

  function matchesSearch(r) {
    const q = LB.search.trim().toLowerCase();
    return !q || (r.model.name + " " + (r.model.org || "")).toLowerCase().includes(q);
  }

  function visibleRows() {
    const t = D.tasks[LB.task];
    const rows = D.rows
      .filter(r => LB.methods.has(r.method))
      .map(r => ({ model: modelById[r.model], method: methodById[r.method], vals: r[LB.task], isBaseline: false }))
      .filter(matchesSearch);
    // Classic IR is a non-agent reference baseline — kept separate so it never competes for rank/best.
    const baseline = [];
    if (LB.task === "search" && LB.classicIR) {
      const b = { model: { name: "Classic IR", org: null, size: -1 }, method: { name: "non-agent", id: "ir", short: "Classic IR" }, vals: D.classicIR, isBaseline: true };
      if (matchesSearch(b)) baseline.push(b);
    }
    return { rows, baseline, metrics: t.metrics, primary: t.primary };
  }

  function computeExtrema(rows, metrics) {
    const ex = {};
    metrics.forEach(m => {
      const vals = rows.map(r => r.vals[m.k]).filter(v => v != null && !Number.isNaN(v));
      ex[m.k] = vals.length ? { min: Math.min(...vals), max: Math.max(...vals) } : { min: 0, max: 0 };
    });
    return ex;
  }

  // best & second-best distinct values honoring direction; suppressed when a column is all-equal/single.
  function bestSecond(rows, m) {
    const vals = rows.map(r => r.vals[m.k]).filter(v => v != null && !Number.isNaN(v));
    const uniq = [...new Set(vals)].sort((a, b) => m.lower ? a - b : b - a);
    if (uniq.length < 2) return { best: NaN, second: NaN };
    return { best: uniq[0], second: uniq[1] };
  }

  function metricCell(r, m, ex, bs, allowHL) {
    const v = r.vals[m.k];
    if (v == null || Number.isNaN(v)) return `<td class="cell-val is-na"><span class="v">—</span></td>`;
    const { min, max } = ex[m.k];
    let frac = (max === min) ? 0 : (m.lower ? (max - v) / (max - min) : (v - min) / (max - min));
    frac = Math.max(0, Math.min(1, frac));
    frac = 0.12 + frac * 0.88;
    const cls = !allowHL ? "" : (v === bs[m.k].best ? "is-best" : (v === bs[m.k].second ? "is-second" : ""));
    return `<td class="cell-val ${cls}"><span class="v">${v.toFixed(2)}</span><span class="bar" style="width:${(frac * 46).toFixed(1)}px"></span></td>`;
  }

  function rowHTML(r, rankLabel, top1, metrics, ex, bs) {
    const org = r.model.org;
    const orgTag = org ? `<span class="m-org org-${org}">${org}</span>` : "";
    const mClass = r.method.id === "classical" ? "m-classical" : r.method.id === "multi" ? "m-multi" : "";
    const cells = metrics.map(m => metricCell(r, m, ex, bs, !r.isBaseline)).join("");
    return `
      <tr class="${r.isBaseline ? "is-baseline" : ""}">
        <td class="cell-rank ${top1 ? "top1" : ""}">${rankLabel}</td>
        <td class="cell-model"><span class="m-name">${r.model.name}</span>${orgTag}</td>
        <td class="cell-method"><span class="tag-method ${mClass}">${r.method.name}</span></td>
        ${cells}
      </tr>`;
  }

  function render() {
    const { rows, baseline, metrics, primary } = visibleRows();
    const ex = computeExtrema(rows, metrics); // extrema/best from agent rows only (baseline excluded)
    const bs = {}; metrics.forEach(m => bs[m.k] = bestSecond(rows, m));

    const sortKey = LB.sortKey || primary;
    const sortMeta = metrics.find(m => m.k === sortKey) || metrics.find(m => m.k === primary);
    const dir = LB.sortDir || (sortMeta.lower ? "asc" : "desc");
    rows.sort((a, b) => {
      const va = a.vals[sortKey], vb = b.vals[sortKey];
      const aN = va == null || Number.isNaN(va), bN = vb == null || Number.isNaN(vb);
      if (aN && bN) return 0; if (aN) return 1; if (bN) return -1;     // nulls always last
      return dir === "asc" ? va - vb : vb - va;
    });

    // head — sortable headers are focusable buttons exposing aria-sort
    $("#lbHead").innerHTML = `
      <tr>
        <th class="col-rank" scope="col">#</th>
        <th class="col-model" scope="col">Model</th>
        <th class="col-method" scope="col">Strategy</th>
        ${metrics.map(m => {
          const sorted = m.k === sortKey;
          const arr = sorted ? (dir === "asc" ? "▲" : "▼") : "";
          const ariaSort = sorted ? (dir === "asc" ? "ascending" : "descending") : "none";
          return `<th data-sort="${m.k}" scope="col" role="button" tabindex="0" aria-sort="${ariaSort}"
            aria-label="Sort by ${m.label}${m.lower ? ", lower is better" : ""}" class="${sorted ? "sorted" : ""}">${m.label}${m.lower ? " ↓" : ""}<span class="arr" aria-hidden="true">${arr}</span></th>`;
        }).join("")}
      </tr>`;
    const doSort = k => {
      const meta = metrics.find(m => m.k === k); if (!meta) return;
      if (LB.sortKey === k) LB.sortDir = LB.sortDir === "asc" ? "desc" : "asc";
      else { LB.sortKey = k; LB.sortDir = meta.lower ? "asc" : "desc"; }
      render();
    };
    $$("#lbHead th[data-sort]").forEach(th => {
      th.addEventListener("click", () => doSort(th.dataset.sort));
      th.addEventListener("keydown", e => {
        if (e.key === "Enter" || e.key === " ") { e.preventDefault(); doSort(th.dataset.sort); }
      });
    });

    // body
    if (rows.length === 0 && baseline.length === 0) {
      $("#lbBody").innerHTML = `<tr><td colspan="${metrics.length + 3}" style="text-align:center;padding:32px;color:var(--ink-faint)">No models match your filter.</td></tr>`;
    } else {
      const agentHTML = rows.map((r, i) => rowHTML(r, String(i + 1), i === 0, metrics, ex, bs)).join("");
      const baseHTML = baseline.map(r => rowHTML(r, "—", false, metrics, ex, bs)).join("");
      $("#lbBody").innerHTML = agentHTML + baseHTML;
    }

    // panel association + note
    const panel = $("#lbPanel");
    if (panel) panel.setAttribute("aria-labelledby", `tab-${LB.task}`);
    const t = D.tasks[LB.task];
    $("#lbNote").innerHTML =
      `${rows.length} ${rows.length === 1 ? "entry" : "entries"}${baseline.length ? " + 1 reference" : ""} · ${t.name} (${t.samples} samples, ${t.dataset}) · sorted by <b>${sortMeta.label}</b> ${dir === "asc" ? "ascending" : "descending"}. ` +
      `<span class="legend-best">● best</span> &nbsp; <span class="legend-second">● 2nd</span> per column.`;

    $("#lbClassicIRWrap").style.display = LB.task === "search" ? "" : "none";
  }

  // controls (present only on the leaderboard page)
  const lbClassicIR = $("#lbClassicIR");
  if (lbClassicIR) lbClassicIR.addEventListener("change", e => { LB.classicIR = e.target.checked; render(); });
  const lbSearchEl = $("#lbSearch");
  if (lbSearchEl) lbSearchEl.addEventListener("input", e => { LB.search = e.target.value; render(); });

  /* ---------------- Supporting tables ---------------- */
  function fmt(v, d = 2) { return v == null ? "—" : v.toFixed(d); }

  function renderFailure() {
    const head = `<tr>
        <th rowspan="2">Model</th>
        <th colspan="2" class="ctr bdiv">Web Search</th>
        <th colspan="2" class="ctr bdiv">Web Rec.</th>
        <th colspan="2" class="ctr">QA</th></tr>
      <tr>
        <th class="ctr">User</th><th class="ctr bdiv">Content</th>
        <th class="ctr">User</th><th class="ctr bdiv">Content</th>
        <th class="ctr">User</th><th class="ctr">Content</th></tr>`;
    const body = D.failure.map(r =>
      `<tr><td>${r.model}</td>
        <td class="ctr">${fmt(r.search[0])}</td><td class="ctr bdiv">${fmt(r.search[1])}</td>
        <td class="ctr">${fmt(r.rec[0])}</td><td class="ctr bdiv">${fmt(r.rec[1])}</td>
        <td class="ctr">${fmt(r.qa[0])}</td><td class="ctr">${fmt(r.qa[1])}</td></tr>`).join("");
    $("#failTable").innerHTML =
      `<table class="dt"><thead>${head}</thead><tbody>${body}</tbody></table>
       <div style="padding:10px 14px;font-size:.78rem;color:var(--ink-faint);display:flex;gap:18px;align-items:center;border-top:1px solid var(--line)">
         <span><span style="display:inline-block;width:11px;height:11px;border-radius:3px;background:var(--brand);vertical-align:-1px;margin-right:5px"></span>User agent</span>
         <span><span style="display:inline-block;width:11px;height:11px;border-radius:3px;background:var(--accent);vertical-align:-1px;margin-right:5px"></span>Content agents</span>
         <span>· each row sums to 100%</span>
       </div>`;
  }

  /* ---------------- Copy BibTeX ---------------- */
  const copyBtn = $("#copyBib");
  if (copyBtn) copyBtn.addEventListener("click", async () => {
    const txt = $("#bibtex").textContent;
    try { await navigator.clipboard.writeText(txt); }
    catch { const ta = document.createElement("textarea"); ta.value = txt; document.body.appendChild(ta); ta.select(); document.execCommand("copy"); ta.remove(); }
    const label = $("#copyBibLabel");
    copyBtn.classList.add("copied"); if (label) label.textContent = "Copied!";
    setTimeout(() => { copyBtn.classList.remove("copied"); if (label) label.textContent = "Copy"; }, 1800);
  });

  /* ---------------- Init (each block runs only if its target exists) ---------------- */
  if ($("#taskCards")) renderTaskCards();                         // Benchmark page
  if ($("#lbTable")) {                                            // Leaderboard page
    buildTaskTabs();
    $("#lbTasks").addEventListener("keydown", onTabKey);          // roving arrow-key tab nav
    buildMethodFilters();
    render();
  }
  if ($("#failTable")) renderFailure();
})();
