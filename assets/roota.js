/* ============================================================
   ROOTA — Shared behavior
   Vanilla, dependency-free. Guards for reduced-motion & perf.
   ============================================================ */
(function () {
  "use strict";

  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const $ = (s, c = document) => c.querySelector(s);
  const $$ = (s, c = document) => Array.from(c.querySelectorAll(s));

  /* ---- Nav: shrink/glass on scroll ---- */
  const nav = $(".nav");
  if (nav) {
    let ticking = false;
    const onScroll = () => {
      nav.classList.toggle("scrolled", window.scrollY > 24);
      ticking = false;
    };
    window.addEventListener("scroll", () => {
      if (!ticking) { requestAnimationFrame(onScroll); ticking = true; }
    }, { passive: true });
    onScroll();
  }

  /* ---- Mobile menu ---- */
  const menuBtn = $(".menu-btn");
  const navLinks = $(".nav-links");
  const scrim = $(".scrim");
  if (menuBtn && navLinks) {
    const close = () => {
      menuBtn.classList.remove("open");
      navLinks.classList.remove("open");
      scrim && scrim.classList.remove("open");
      menuBtn.setAttribute("aria-expanded", "false");
      document.body.style.overflow = "";
    };
    menuBtn.addEventListener("click", () => {
      const open = navLinks.classList.toggle("open");
      menuBtn.classList.toggle("open", open);
      scrim && scrim.classList.toggle("open", open);
      menuBtn.setAttribute("aria-expanded", String(open));
      document.body.style.overflow = open ? "hidden" : "";
    });
    scrim && scrim.addEventListener("click", close);
    $$(".nav-links a").forEach((a) => a.addEventListener("click", close));
    window.addEventListener("keydown", (e) => { if (e.key === "Escape") close(); });
  }

  /* ---- Active nav link by path ---- */
  const here = location.pathname.replace(/\/$/, "");
  $$(".nav-links a").forEach((a) => {
    const href = (a.getAttribute("href") || "").replace(/\/$/, "");
    if (href && !href.startsWith("#") && href === here) a.classList.add("active");
  });

  /* ---- Split headings into chars (for .split reveal) ---- */
  function splitChars(el) {
    const walk = (node) => {
      Array.from(node.childNodes).forEach((child) => {
        if (child.nodeType === 3) {
          const frag = document.createDocumentFragment();
          child.textContent.split(/(\s+)/).forEach((part) => {
            if (part === "") return;
            if (/^\s+$/.test(part)) {
              frag.appendChild(document.createTextNode(part));
              return;
            }
            const word = document.createElement("span");
            word.className = "word";
            Array.from(part).forEach((ch) => {
              const s = document.createElement("span");
              s.className = "ch";
              s.textContent = ch;
              word.appendChild(s);
            });
            frag.appendChild(word);
          });
          child.replaceWith(frag);
        } else if (child.nodeType === 1 && child.tagName !== "BR") {
          walk(child);
        }
      });
    };
    walk(el);
    // stagger
    $$(".ch", el).forEach((c, i) => (c.style.transitionDelay = (i * 0.022) + "s"));
  }
  $$(".split").forEach(splitChars);

  /* ---- IntersectionObserver reveals ---- */
  const revealTargets = $$(".reveal, .split");
  if (revealTargets.length) {
    if (reduced) {
      revealTargets.forEach((el) => el.classList.add("in"));
    } else {
      const io = new IntersectionObserver((entries) => {
        entries.forEach((e) => e.target.classList.toggle("in", e.isIntersecting));
      }, { threshold: 0.12, rootMargin: "0px 0px -6% 0px" });
      revealTargets.forEach((el) => io.observe(el));
      // ensure above-the-fold split heading shows immediately
      requestAnimationFrame(() => {
        revealTargets.forEach((el) => {
          const r = el.getBoundingClientRect();
          if (r.top < window.innerHeight * 0.9) el.classList.add("in");
        });
      });
    }
  }

  /* ---- Spotlight cards (mouse-follow) ---- */
  if (!reduced) {
    $$(".spotlight").forEach((card) => {
      card.addEventListener("pointermove", (e) => {
        const r = card.getBoundingClientRect();
        card.style.setProperty("--mx", (e.clientX - r.left) + "px");
        card.style.setProperty("--my", (e.clientY - r.top) + "px");
      });
    });
  }

  /* ---- Number scramble on view [data-scramble] ---- */
  const CH = "ABCDEFGHJKLMNPQRSTUVWXYZ0123456789/+.<>";
  function scramble(el) {
    const final = el.dataset.scramble;
    if (reduced) { el.textContent = final; return; }
    const frames = 22;
    let f = 0;
    clearInterval(el._t);
    el._t = setInterval(() => {
      f++;
      const reveal = Math.floor((f / frames) * final.length);
      let out = "";
      for (let i = 0; i < final.length; i++) {
        out += (final[i] === " ") ? " " : (i < reveal ? final[i] : CH[(Math.random() * CH.length) | 0]);
      }
      el.textContent = out;
      if (f >= frames) { el.textContent = final; clearInterval(el._t); }
    }, 38);
  }
  const scrambles = $$("[data-scramble]");
  if (scrambles.length) {
    const io = new IntersectionObserver((entries) => {
      entries.forEach((e) => { if (e.isIntersecting) { scramble(e.target); io.unobserve(e.target); } });
    }, { threshold: 0.6 });
    scrambles.forEach((el) => io.observe(el));
  }

  /* ---- Count up [data-count] ---- */
  function countUp(el) {
    const target = parseFloat(el.dataset.count);
    const suffix = el.dataset.suffix || "";
    const dec = (el.dataset.count.split(".")[1] || "").length;
    if (reduced) { el.textContent = target.toFixed(dec) + suffix; return; }
    const dur = 1300, start = performance.now();
    const step = (now) => {
      const p = Math.min((now - start) / dur, 1);
      const e = 1 - Math.pow(1 - p, 3);
      el.textContent = (target * e).toFixed(dec) + suffix;
      if (p < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }
  const counters = $$("[data-count]");
  if (counters.length) {
    const io = new IntersectionObserver((entries) => {
      entries.forEach((e) => { if (e.isIntersecting) { countUp(e.target); io.unobserve(e.target); } });
    }, { threshold: 0.6 });
    counters.forEach((el) => io.observe(el));
  }

  /* ---- Copy buttons [data-copy] ---- */
  $$("[data-copy]").forEach((btn) => {
    btn.addEventListener("click", () => {
      navigator.clipboard.writeText(btn.dataset.copy).then(() => {
        const label = btn.querySelector("[data-copy-label]") || btn;
        const old = label.textContent;
        label.textContent = "Copied";
        btn.classList.add("copied");
        setTimeout(() => { label.textContent = old; btn.classList.remove("copied"); }, 1600);
      }).catch(() => {});
    });
  });

  /* ---- Reusable typewriter terminal ----
     Usage: <div class="term-body" data-term='[{"t":"...","c":"c-err","d":300}]'></div>
     or call Roota.typeTerminal(el, lines).
  ------------------------------------------------------------ */
  function typeTerminal(el, lines) {
    el.innerHTML = "";
    if (reduced) {
      lines.forEach((l) => {
        const s = document.createElement("span");
        s.className = l.c || "";
        s.textContent = l.t.replace(/\n/g, "\n");
        el.appendChild(s);
      });
      const cur = document.createElement("span");
      cur.className = "caret";
      el.appendChild(cur);
      return;
    }
    lines.forEach((line) => {
      setTimeout(() => {
        const span = document.createElement("span");
        span.className = line.c || "";
        el.appendChild(span);
        let i = 0;
        const txt = line.t;
        const iv = setInterval(() => {
          if (i < txt.length) {
            if (txt[i] === "\n") span.appendChild(document.createElement("br"));
            else span.appendChild(document.createTextNode(txt[i]));
            i++;
            el.scrollTop = el.scrollHeight;
          } else { clearInterval(iv); }
        }, 15);
      }, line.d || 0);
    });
    const last = lines[lines.length - 1];
    setTimeout(() => {
      const cur = document.createElement("span");
      cur.className = "caret";
      el.appendChild(cur);
    }, (last.d || 0) + last.t.length * 15 + 120);
  }

  $$("[data-term]").forEach((el) => {
    let lines;
    try { lines = JSON.parse(el.dataset.term); } catch (e) { return; }
    const loop = el.dataset.termLoop === "true";
    const total = (lines[lines.length - 1].d || 0) + 2500;
    const run = () => typeTerminal(el, lines);
    const io = new IntersectionObserver((entries) => {
      entries.forEach((e) => {
        if (e.isIntersecting && !el._started) {
          el._started = true;
          run();
          if (loop && !reduced) setInterval(run, total + 6000);
        }
      });
    }, { threshold: 0.3 });
    io.observe(el);
  });

  /* ---- Year injection ---- */
  $$("[data-year]").forEach((el) => (el.textContent = new Date().getFullYear()));

  /* ---- Expose ---- */
  window.Roota = { typeTerminal, scramble, countUp };
})();
