/* QuestFinder — chat thread: render, send (text or photo) and poll for new messages every 3 s. */
(function () {
  "use strict";
  const form = document.getElementById("chatForm");
  if (!form) return;
  const log = document.getElementById("chatLog");
  const bodyInput = document.getElementById("chatBody");
  const imageInput = document.getElementById("chatImage");
  const preview = document.getElementById("chatImagePreview");
  const POLL_MS = 3000;
  let lastId = 0;
  let sending = false;
  const seen = new Set();

  function atBottom() { return window.innerHeight + window.scrollY >= document.body.scrollHeight - 80; }
  function scrollDown() { window.scrollTo({ top: document.body.scrollHeight }); }

  function render(m) {
    if (seen.has(m.id)) return;
    seen.add(m.id);
    lastId = Math.max(lastId, m.id);
    const row = document.createElement("div");
    row.className = "bubble-row " + (m.mine ? "mine" : "theirs");
    let html = '<div class="bubble">';
    if (m.image) html += `<a href="${m.image}" target="_blank" rel="noopener"><img src="${m.image}" alt="Photo" loading="lazy"></a>`;
    if (m.body) html += `<p>${QF.escape(m.body)}</p>`;
    html += `<time>${QF.escape(m.time)}</time></div>`;
    row.innerHTML = html;
    log.appendChild(row);
  }

  function renderMany(list) {
    const stick = atBottom();
    list.forEach(render);
    if (stick || list.some((m) => m.mine)) scrollDown();
  }

  async function poll() {
    try {
      const data = await QF.fetchJSON(`${form.dataset.poll}?after=${lastId}`);
      if (data.messages.length) renderMany(data.messages);
    } catch (_) { /* network hiccup: try again next tick */ }
  }

  imageInput.addEventListener("change", () => {
    const f = imageInput.files[0];
    if (f) { preview.src = URL.createObjectURL(f); preview.hidden = false; }
    else { preview.hidden = true; }
  });
  preview.addEventListener("click", () => { imageInput.value = ""; preview.hidden = true; });

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (sending) return;
    const text = bodyInput.value.trim();
    const file = imageInput.files[0];
    if (!text && !file) return;
    sending = true;
    const data = new FormData();
    data.append("body", text);
    if (file) data.append("image", file);
    try {
      const res = await QF.fetchJSON(form.dataset.send, { method: "POST", body: data });
      bodyInput.value = "";
      imageInput.value = "";
      preview.hidden = true;
      renderMany([res.message]);
    } catch (err) {
      alertBar(err.message);
    } finally {
      sending = false;
      bodyInput.focus();
    }
  });

  function alertBar(text) {
    const div = document.createElement("div");
    div.className = "flash flash-danger";
    div.innerHTML = `<span>${QF.escape(text)}</span><button type="button" class="flash-close" data-dismiss>&times;</button>`;
    log.appendChild(div);
    scrollDown();
  }

  renderMany(window.QF_CHAT_INITIAL || []);
  scrollDown();
  setInterval(() => { if (!document.hidden) poll(); }, POLL_MS);
})();
