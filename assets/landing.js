/* Roota landing — self-contained behavior. Vanilla JS, no deps. */
(function () {
  "use strict";
  const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const $ = (s, r) => (r || document).querySelector(s);
  const $$ = (s, r) => Array.from((r || document).querySelectorAll(s));

  /* ---------- nav ---------- */
  const nav = $("#nav");
  let navTick = false;
  addEventListener("scroll", () => {
    if (navTick) return;
    navTick = true;
    requestAnimationFrame(() => {
      nav.classList.toggle("scrolled", scrollY > 8);
      navTick = false;
    });
  }, { passive: true });
  nav.classList.toggle("scrolled", scrollY > 8);

  const menuBtn = $(".menu-btn");
  const navLinks = $("#navLinks");
  menuBtn.addEventListener("click", () => {
    const open = navLinks.classList.toggle("open");
    menuBtn.setAttribute("aria-expanded", String(open));
  });
  navLinks.addEventListener("click", (e) => {
    if (e.target.tagName === "A") {
      navLinks.classList.remove("open");
      menuBtn.setAttribute("aria-expanded", "false");
    }
  });

  /* ---------- reveals ---------- */
  const rv = $$(".rv");
  if (reduced || !("IntersectionObserver" in window)) {
    rv.forEach((el) => el.classList.add("in"));
  } else {
    const io = new IntersectionObserver((entries) => {
      entries.forEach((e) => {
        if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); }
      });
    }, { threshold: 0.12, rootMargin: "0px 0px -8% 0px" });
    rv.forEach((el) => io.observe(el));
  }

  $$("[data-year]").forEach((el) => (el.textContent = new Date().getFullYear()));

  const pad2 = (n) => String(n + 1).padStart(2, "0");

  /* ---------- hero scope: the log stream of incident #142 ---------- */
  // weight drives the waveform amplitude — how "loud" each log event is
  const LOGEV = [
    { msg: "INFO  request /api/session/9981",        level: "info",  status: "ok",   weight: 220 },
    { msg: "INFO  UserService.get_session(9981)",    level: "info",  status: "ok",   weight: 180 },
    { msg: "DEBUG active_sessions size=812",         level: "debug", status: "ok",   weight: 130 },
    { msg: "WARN  session cache miss",               level: "warn",  status: "warn", weight: 340 },
    { msg: "ERROR KeyError: 9981",                   level: "error", status: "err",  weight: 720 },
    { msg: "ERROR traceback user_session.py:6",      level: "error", status: "err",  weight: 560 },
    { msg: "FATAL request 500 — worker recycled",    level: "fatal", status: "err",  weight: 960 },
  ];

  const canvas = $("#scope");
  const roFrame = $("#roFrame"), roStep = $("#roStep"), roState = $("#roState");
  const clock = $("#scopeClock");
  if (canvas) {
    const ctx = canvas.getContext("2d");
    const css = getComputedStyle(document.documentElement);
    const C = {
      ok: css.getPropertyValue("--green").trim() || "#34e28a",
      warn: css.getPropertyValue("--amber").trim() || "#f2b45c",
      err: css.getPropertyValue("--red").trim() || "#ff6459",
      line: "rgba(226,236,229,0.10)",
      base: "rgba(226,236,229,0.28)",
    };
    let W = 0, H = 0, dpr = 1;
    const noise = Array.from({ length: 160 }, () => Math.random() * 2 - 1);

    function resize() {
      const r = canvas.getBoundingClientRect();
      dpr = Math.min(devicePixelRatio || 1, 2);
      W = Math.max(1, Math.round(r.width));
      H = Math.max(1, Math.round(r.height));
      canvas.width = W * dpr;
      canvas.height = H * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }
    resize();
    addEventListener("resize", resize, { passive: true });

    const total = LOGEV.reduce((a, s) => a + s.weight, 0);
    const seg = [];
    let acc = 0;
    LOGEV.forEach((s) => { seg.push({ from: acc / total, to: (acc + s.weight) / total, s }); acc += s.weight; });
    const stepAt = (p) => seg.findIndex((g) => p >= g.from && p <= g.to);
    const N = LOGEV.length;

    function draw(p) {
      ctx.clearRect(0, 0, W, H);
      const base = H * 0.62;
      const padX = 6;
      const iw = W - padX * 2;

      ctx.strokeStyle = C.line;
      ctx.lineWidth = 1;
      seg.forEach((g) => {
        const x = padX + g.from * iw;
        ctx.beginPath(); ctx.moveTo(x, 8); ctx.lineTo(x, H - 8); ctx.stroke();
      });

      const upto = Math.max(0.002, p);
      const steps = 220;
      ctx.lineWidth = 1.6;
      let prevIdx = -1;
      ctx.beginPath();
      for (let i = 0; i <= steps; i++) {
        const t = (i / steps) * upto;
        const x = padX + t * iw;
        const gi = stepAt(t);
        const g = seg[Math.max(0, gi)];
        const local = (t - g.from) / (g.to - g.from || 1);
        const amp = 6 + (g.s.weight / 960) * (H * 0.34);
        const burst = Math.sin(local * Math.PI);
        const n = noise[Math.floor(t * 159)] * 3;
        const y = base - burst * amp + n;
        if (gi !== prevIdx && prevIdx !== -1) {
          ctx.strokeStyle = seg[prevIdx].s.status === "err" ? C.err : seg[prevIdx].s.status === "warn" ? C.warn : C.ok;
          ctx.stroke();
          ctx.beginPath();
          ctx.moveTo(x, y);
        } else if (i === 0) {
          ctx.moveTo(x, y);
        } else {
          ctx.lineTo(x, y);
        }
        prevIdx = gi;
      }
      ctx.strokeStyle = seg[Math.max(0, prevIdx)].s.status === "err" ? C.err : seg[Math.max(0, prevIdx)].s.status === "warn" ? C.warn : C.ok;
      ctx.stroke();

      ctx.strokeStyle = C.line;
      ctx.beginPath();
      ctx.moveTo(padX + upto * iw, base);
      ctx.lineTo(padX + iw, base);
      ctx.stroke();

      const px = padX + upto * iw;
      ctx.strokeStyle = C.base;
      ctx.beginPath(); ctx.moveTo(px, 4); ctx.lineTo(px, H - 4); ctx.stroke();

      const gi = Math.max(0, stepAt(Math.min(upto, 0.999)));
      const ev = LOGEV[gi];
      roFrame.textContent = pad2(gi) + "/" + pad2(N - 1);
      roStep.textContent = ev.msg;
      roState.textContent = ev.level;
      roState.className = "status-" + ev.status;
      clock.textContent = "t+" + ((upto * total) / 1000).toFixed(2) + "s";
    }

    if (reduced) {
      draw(1);
    } else {
      let playing = true, hover = false, hoverP = 0;
      let start = performance.now();
      const DUR = 5200, HOLD = 1600;
      let raf = null;
      function loop(now) {
        raf = null;
        if (hover) { draw(hoverP); }
        else {
          const el = (now - start) % (DUR + HOLD);
          draw(Math.min(1, el / DUR));
        }
        if (playing) raf = requestAnimationFrame(loop);
      }
      const vis = new IntersectionObserver((es) => {
        es.forEach((e) => {
          const on = e.isIntersecting;
          if (on && !playing) { playing = true; start = performance.now(); raf = requestAnimationFrame(loop); }
          else if (on && playing && raf === null) { raf = requestAnimationFrame(loop); }
          else if (!on) { playing = false; if (raf) { cancelAnimationFrame(raf); raf = null; } }
        });
      }, { threshold: 0.1 });
      vis.observe(canvas);
      canvas.addEventListener("pointermove", (e) => {
        const r = canvas.getBoundingClientRect();
        hover = true;
        hoverP = Math.min(1, Math.max(0.002, (e.clientX - r.left - 6) / (r.width - 12)));
      });
      canvas.addEventListener("pointerleave", () => { hover = false; start = performance.now(); });
      raf = requestAnimationFrame(loop);
    }
  }

  /* ---------- pipeline demo: raw log → fixed line ---------- */
  const STAGES = [
    { name: "parse:service.log",      kind: "parser", lat: "0.4s", status: "ok" },
    { name: "extract:files",          kind: "parser", lat: "0.1s", status: "ok" },
    { name: "fetch:repo_tree",        kind: "github", lat: "0.8s", status: "ok" },
    { name: "disambiguate:2_matches", kind: "github", lat: "0.3s", status: "warn", note: "2 matches" },
    { name: "fetch:source@main",      kind: "github", lat: "0.6s", status: "ok" },
    { name: "analyze:grounded",       kind: "ai",     lat: "3.2s", status: "ok" },
    { name: "diagnosis:exact_fix",    kind: "ai",     lat: "done", status: "ok" },
  ];
  const N = STAGES.length;

  const STATES = [
    { kv: [
        ["log.file", "service.log"],
        ["lines.parsed", "1,248"],
        ["errors", "3", { changed: true }],
        ["warnings", "1"],
        ["format", "structured text — regex path"],
      ],
      note: { cls: "", lbl: "fallback", text: "If the regex parser can't read a format, Roota hands the raw text to an AI parser — JSON, Node errors, syslog, anything." } },
    { kv: [
        ["files.mentioned", '["user_session.py"]', { changed: true }],
        ["function", "get_session()", { changed: true }],
        ["traceback.line", "6"],
      ] },
    { kv: [
        ["repo", "myorg/api"],
        ["branch", "main — auto-detected", { changed: true }],
        ["tree.files", "412"],
        ["candidates", "2 × user_session.py", { changed: true }],
      ] },
    { kv: [
        ["tests/user_session.py", "✗ test file — dropped", { err: true }],
        ["src/services/user_session.py", "✓ contains def get_session", { changed: true }],
        ["resolved", "src/services/user_session.py", { changed: true }],
      ],
      note: { cls: "", lbl: "three-stage disambiguation", text: "Filename match → drop test files → verify the function actually exists in the candidate. Roota analyzes the right file, not a coincidental name match." } },
    { kv: [
        ["source", "raw.githubusercontent.com @ main"],
        ["file", "src/services/user_session.py"],
        ["lines.fetched", "84", { changed: true }],
      ] },
    { kv: [
        ["context", "3 errors · 1 warning · real source", { changed: true }],
        ["grounding", "actual file contents — not a stack-trace guess"],
        ["model", "structured diagnosis prompt"],
      ] },
    { kv: [
        ["root.cause", "unguarded dict access in get_session()", { changed: true }],
        ["cascade", "500s on /api/session — worker recycled"],
        ["confidence", "10/10", { changed: true }],
      ],
      fix: {
        del: "-  return self.active_sessions[user_id]",
        add: "+  return self.active_sessions.get(user_id)",
      },
      note: { cls: "err-note", lbl: "fix · user_session.py:6", text: "The corrected line uses your actual variable names — because Roota read the actual file." } },
  ];

  const stepsPane = $("#stepsPane");
  const statePane = $("#statePane");
  const tPrev = $("#tPrev"), tNext = $("#tNext"), tPlay = $("#tPlay");
  const tScrub = $("#tScrub"), tPos = $("#tPos");
  const diffToggle = $("#diffToggle");
  if (stepsPane) {
    let frame = 0;
    let cppMode = false;
    let playTimer = null;

    const GLYPH = { ok: "✓", warn: "▲", err: "✗" };
    STAGES.forEach((s, i) => {
      const b = document.createElement("button");
      b.className = "step";
      b.setAttribute("role", "listitem");
      b.innerHTML =
        '<span class="idx">' + pad2(i) + "</span>" +
        '<span class="glyph ' + s.status + '">' + GLYPH[s.status] + "</span>" +
        '<span><span class="kind">' + s.kind + " · </span>" + s.name + "</span>" +
        '<span class="lat">' + s.lat + (s.note ? " · " + s.note : "") + "</span>";
      b.addEventListener("click", () => { stopPlay(); if (cppMode) toggleCpp(false); setFrame(i); });
      stepsPane.appendChild(b);
    });
    const stepEls = $$(".step", stepsPane);

    function esc(str) {
      return String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    }

    function renderState() {
      const st = STATES[frame];
      const s = STAGES[frame];
      let html =
        '<div class="state-title"><span>pipeline state</span><span class="frame">stage ' +
        pad2(frame) + " · " + esc(s.name) + "</span></div>";
      html += '<div class="kv">';
      st.kv.forEach(([k, v, m]) => {
        m = m || {};
        html +=
          '<span class="k">' + esc(k) + "</span>" +
          '<span class="v' + (m.changed ? " changed" : "") + (m.err ? " err" : "") + '">' + esc(v) + "</span>";
      });
      html += "</div>";
      if (st.fix) {
        html +=
          '<div class="fix-block"><span class="fl del">' + esc(st.fix.del) +
          '</span><span class="fl add">' + esc(st.fix.add) + "</span></div>";
      }
      if (st.note) {
        html +=
          '<div class="state-note ' + st.note.cls + '"><span class="lbl">' + esc(st.note.lbl) +
          "</span>" + esc(st.note.text) + "</div>";
      }
      statePane.innerHTML = html;
    }

    function renderCpp() {
      const LINES = [
        ["crash_report_1783653301.log — written by debugai_handler.h", "same"],
        ["SIGNAL: 11 (SIGSEGV)", "div-b"],
        ["CRASH_ADDRESS: 0x60b82188d451", "div-b"],
        ["BASE_MAP: 60b82188b000 → file offset 0x2451", "same"],
        ["$ addr2line -e ./pool_server 0x2451", "same"],
        ["→ allocator.cpp:212 — Pool::release()", "div-a"],
        ["fetch: myorg/pool-server @ main · allocator.cpp", "same"],
        ["diagnosis: double-free in Pool::release() · confidence 10/10", "div-a"],
      ];
      let html =
        '<div class="state-title"><span>c++ crash flow</span><span class="frame">segfault → exact line, no debugger</span></div>';
      LINES.forEach(([t, c]) => { html += '<div class="dline ' + c + '">' + t.replace(/</g, "&lt;") + "</div>"; });
      html +=
        '<div class="state-note"><span class="lbl">why confidence 10/10</span>' +
        "The failing line comes from the memory address itself — resolved with addr2line, not inferred from text. The handler is a single header file, two lines to install, signal-safe, and speaks both Windows SEH and POSIX signals.</div>";
      statePane.innerHTML = html;
    }

    function setFrame(i) {
      frame = Math.max(0, Math.min(N - 1, i));
      stepEls.forEach((el, j) => {
        el.classList.toggle("active", j === frame);
        el.classList.toggle("future", j > frame);
      });
      tScrub.value = String(frame);
      tPos.textContent = pad2(frame) + " / " + pad2(N - 1);
      if (!cppMode) renderState();
    }

    function stopPlay() {
      if (playTimer) { clearInterval(playTimer); playTimer = null; }
      tPlay.setAttribute("aria-pressed", "false");
      tPlay.textContent = "▶";
    }
    function startPlay() {
      if (cppMode) toggleCpp(false);
      if (frame >= N - 1) setFrame(0);
      tPlay.setAttribute("aria-pressed", "true");
      tPlay.textContent = "❚❚";
      playTimer = setInterval(() => {
        if (frame >= N - 1) { stopPlay(); return; }
        setFrame(frame + 1);
      }, 900);
    }

    function toggleCpp(on) {
      cppMode = on === undefined ? !cppMode : on;
      diffToggle.setAttribute("aria-pressed", String(cppMode));
      if (cppMode) { stopPlay(); renderCpp(); } else { renderState(); }
    }

    tPrev.addEventListener("click", () => { stopPlay(); if (cppMode) toggleCpp(false); setFrame(frame - 1); });
    tNext.addEventListener("click", () => { stopPlay(); if (cppMode) toggleCpp(false); setFrame(frame + 1); });
    tPlay.addEventListener("click", () => (playTimer ? stopPlay() : startPlay()));
    tScrub.addEventListener("input", () => { stopPlay(); if (cppMode) toggleCpp(false); setFrame(Number(tScrub.value)); });
    diffToggle.addEventListener("click", () => toggleCpp());

    let dbgVisible = false;
    new IntersectionObserver((es) => es.forEach((e) => (dbgVisible = e.isIntersecting)), { threshold: 0.2 })
      .observe($(".debugger"));
    document.addEventListener("keydown", (e) => {
      if (!dbgVisible) return;
      const t = e.target;
      if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA")) return;
      if (e.key === "ArrowRight") { stopPlay(); if (cppMode) toggleCpp(false); setFrame(frame + 1); e.preventDefault(); }
      if (e.key === "ArrowLeft") { stopPlay(); if (cppMode) toggleCpp(false); setFrame(frame - 1); e.preventDefault(); }
    });

    setFrame(0);
    if (!reduced) {
      const once = new IntersectionObserver((es) => {
        es.forEach((e) => {
          if (e.isIntersecting) { startPlay(); once.disconnect(); }
        });
      }, { threshold: 0.45 });
      once.observe($(".debugger"));
    } else {
      setFrame(N - 1);
    }
  }

  /* ---------- updates form ---------- */
  const form = $("#wlForm");
  if (form) {
    const email = $("#wlEmail"), btn = $("#wlBtn"), msg = $("#wlMsg");
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const val = email.value.trim();
      msg.className = "wl-msg";
      if (!val || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(val)) {
        msg.textContent = "✗ enter a valid email address";
        msg.classList.add("err");
        return;
      }
      btn.disabled = true;
      const prev = btn.textContent;
      btn.textContent = "…";
      try {
        const fd = new FormData();
        fd.append("email", val);
        const res = await fetch("/waitlist", { method: "POST", body: fd });
        if (!res.ok) throw new Error("bad status " + res.status);
        msg.textContent = "✓ you're on the list — we'll email you when it ships";
        msg.classList.add("ok");
        form.reset();
      } catch (err) {
        msg.textContent = "✗ something went wrong — try again or email us directly";
        msg.classList.add("err");
      } finally {
        btn.disabled = false;
        btn.textContent = prev;
      }
    });
  }
})();
