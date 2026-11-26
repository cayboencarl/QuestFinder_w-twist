/* QuestFinder — shared helpers used on every page (vanilla JS, no framework). */
(function () {
  "use strict";

  const QF = (window.QF = window.QF || {});

  /** CSRF token from <meta name="csrf-token"> for fetch() calls. */
  QF.csrfToken = function () {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute("content") : "";
  };

  /** fetch() wrapper that sends the CSRF token and parses JSON. */
  QF.fetchJSON = async function (url, options = {}) {
    const opts = Object.assign({ credentials: "same-origin" }, options);
    opts.headers = Object.assign({ "X-CSRFToken": QF.csrfToken(), Accept: "application/json" }, opts.headers || {});
    const res = await fetch(url, opts);
    let data = null;
    try { data = await res.json(); } catch (_) { /* non-JSON response */ }
    if (!res.ok) {
      const msg = (data && data.error) || `Request failed (${res.status})`;
      throw new Error(msg);
    }
    return data;
  };

  /** Escape text before inserting it as HTML. */
  QF.escape = function (text) {
    const div = document.createElement("div");
    div.textContent = text == null ? "" : String(text);
    return div.innerHTML;
  };

  // Dismissible flash messages.
  document.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-dismiss]");
    if (btn) btn.parentElement.remove();
  });

  // Two-step confirmation for forms with data-confirm="...".
  // Uses an on-page prompt instead of window.confirm(), which some embedded
  // browsers and in-app web views block (the form would silently never submit).
  document.addEventListener("submit", (e) => {
    const form = e.target;
    const msg = form.getAttribute("data-confirm");
    if (!msg || form.dataset.confirmed === "1") return;
    e.preventDefault();
    const btn = form.querySelector('button[type="submit"], button:not([type])');
    let note = form.querySelector(".confirm-note");
    if (!note) {
      note = document.createElement("p");
      note.className = "confirm-note";
      form.insertBefore(note, btn);
    }
    note.textContent = msg;
    form.dataset.confirmed = "1";
    if (btn) {
      btn.dataset.label = btn.dataset.label || btn.textContent;
      btn.textContent = "Tap again to confirm";
    }
    // Disarm after 15 seconds if not confirmed.
    clearTimeout(form._confirmTimer);
    form._confirmTimer = setTimeout(() => {
      form.dataset.confirmed = "";
      note.remove();
      if (btn) btn.textContent = btn.dataset.label;
    }, 15000);
  });

  // Quick-choice buttons that fill a form's amount + unit fields (admin suspension).
  document.addEventListener("click", (e) => {
    const btn = e.target.closest(".js-preset[data-amount][data-unit]");
    if (!btn || !btn.form) return;
    btn.form.elements.amount.value = btn.dataset.amount;
    btn.form.elements.unit.value = btn.dataset.unit;
  });

  // Show a preview for <input type="file" data-preview="#imgId">.
  document.addEventListener("change", (e) => {
    const input = e.target;
    if (!input.matches('input[type="file"][data-preview]')) return;
    const img = document.querySelector(input.getAttribute("data-preview"));
    const file = input.files && input.files[0];
    if (!img || !file) return;
    img.src = URL.createObjectURL(file);
    img.hidden = false;
  });
})();
