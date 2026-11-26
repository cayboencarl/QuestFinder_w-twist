/* Multi-select skills dropdown (Edit profile). */
(function () {
  "use strict";
  document.querySelectorAll("[data-multi-select]").forEach((box) => {
    const max = parseInt(box.dataset.max, 10) || 8;
    const summary = box.querySelector(".ms-summary");
    const chips = box.parentElement.querySelector("[data-chips]");
    const boxes = Array.from(box.querySelectorAll('input[type="checkbox"]'));
    const search = box.querySelector(".ms-search");

    function render() {
      const chosen = boxes.filter((b) => b.checked);
      summary.textContent = chosen.length ? `${chosen.length} selected` : summary.dataset.placeholder;
      chips.innerHTML = "";
      chosen.forEach((b) => {
        const chip = document.createElement("button");
        chip.type = "button";
        chip.className = "chip";
        chip.innerHTML = `${QF.escape(b.value)} <span aria-hidden="true">×</span>`;
        chip.setAttribute("aria-label", `Remove ${b.value}`);
        chip.addEventListener("click", () => { b.checked = false; render(); });
        chips.appendChild(chip);
      });
      const full = chosen.length >= max;
      boxes.forEach((b) => { b.disabled = full && !b.checked; });
    }

    boxes.forEach((b) => b.addEventListener("change", render));
    search.addEventListener("input", () => {
      const q = search.value.trim().toLowerCase();
      box.querySelectorAll(".ms-option").forEach((opt) => {
        opt.hidden = q && !opt.textContent.toLowerCase().includes(q);
      });
      box.querySelectorAll(".ms-group").forEach((g) => {
        g.hidden = !g.querySelector(".ms-option:not([hidden])");
      });
    });
    // Close when clicking outside.
    document.addEventListener("click", (e) => { if (!box.contains(e.target)) box.open = false; });
    render();
  });
})();
