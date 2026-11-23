const API = "http://localhost:5000/api";
let currentUser = null;

function setUser() {
  currentUser = document.getElementById("userId").value;
  document.getElementById("who").textContent = currentUser ? "Logged in as " + currentUser : "";
}

function headers() {
  return { "Content-Type": "application/json", "X-User-Id": currentUser };
}

function say(text, ok) {
  const el = document.getElementById("message");
  el.className = ok ? "ok" : "error";
  el.textContent = text;
}

function showView(name) {
  for (const v of ["post", "quests", "wallet"]) {
    document.getElementById("view-" + v).hidden = v !== name;
  }
  if (name === "quests") loadQuests();
  if (name === "wallet") loadWallet();
}

async function postTask() {
  const body = {
    title: document.getElementById("title").value,
    description: document.getElementById("description").value,
    skills_required: document.getElementById("skills_required").value,
    location: document.getElementById("location").value,
    budget: parseFloat(document.getElementById("budget").value),
    duration_minutes: parseInt(document.getElementById("duration_minutes").value),
  };
  const res = await fetch(API + "/tasks", { method: "POST", headers: headers(), body: JSON.stringify(body) });
  const data = await res.json();
  if (res.ok) say("Task posted (ID " + data.id + ")", true);
  else say(JSON.stringify(data.errors || data.error), false);
}

async function loadQuests() {
  const search = document.getElementById("search").value;
  const res = await fetch(API + "/tasks" + (search ? "?search=" + encodeURIComponent(search) : ""));
  const tasks = await res.json();
  const list = document.getElementById("quest-list");
  list.innerHTML = tasks.length ? "" : "<p>No open quests.</p>";
  for (const t of tasks) {
    const div = document.createElement("div");
    div.className = "card";
    div.innerHTML = `<b>${t.title}</b> — ₱${t.budget}<br>${t.skills_required} · ${t.location} · ${t.duration_minutes} mins
      <br><button onclick="showTask(${t.id})">View</button>`;
    list.appendChild(div);
  }
}

async function showTask(id) {
  const res = await fetch(API + "/tasks/" + id);
  const t = await res.json();
  document.getElementById("quest-detail").innerHTML = `<div class="card">
    <h3>${t.title}</h3>
    <p>${t.description}</p>
    <p>Qualification: ${t.skills_required}<br>Location: ${t.location}<br>Duration: ${t.duration_minutes} mins<br>Pay: ₱${t.budget}<br>Status: ${t.status}</p>
    <button onclick="completeTask(${t.id})">Mark complete (client)</button>
    ${t.status === "open" ? `<button onclick="loadMatches(${t.id})">See matching residents</button><div id="matches"></div>` : ""}
  </div>`;
}

async function acceptTask(id) {
  const res = await fetch(API + "/tasks/" + id + "/accept", { method: "POST", headers: headers() });
  const data = await res.json();
  if (res.ok) { say("Quest accepted", true); showTask(id); }
  else say(JSON.stringify(data.errors || data.error), false);
}

async function completeTask(id) {
  const res = await fetch(API + "/tasks/" + id + "/complete", { method: "POST", headers: headers() });
  const data = await res.json();
  if (res.ok) say("Task completed. Worker receives ₱" + data.worker_receives, true);
  else say(JSON.stringify(data.errors || data.error), false);
}

async function loadWallet() {
  const bal = await (await fetch(API + "/wallet", { headers: headers() })).json();
  document.getElementById("balance").innerHTML = `<div class="card"><b>Balance: ₱${bal.balance}</b></div>`;
  const tx = await (await fetch(API + "/wallet/transactions", { headers: headers() })).json();
  document.getElementById("transactions").innerHTML = tx.map(t =>
    `<div class="card">Task ${t.task_id} · ${t.role} · ₱${t.amount} (commission ₱${t.commission})</div>`
  ).join("") || "<p>No transactions.</p>";
}

async function loadMatches(id) {
  const res = await fetch(API + "/tasks/" + id + "/matches", { headers: headers() });
  const data = await res.json();
  const box = document.getElementById("matches");
  if (!res.ok) {
    box.innerHTML = `<p class="error">${data.errors || data.error}</p>`;
    return;
  }
  box.innerHTML = data.length
    ? data.map(r => `<div class="card">
        <b>${r.name}</b> · match score ${r.match_score}<br>
        Skills: ${r.skills}<br>Service area: ${r.service_area}
        <br><button onclick="selectWorker(${id}, ${r.user_id})">Select this worker</button>
      </div>`).join("")
    : "<p>No matching residents in this area.</p>";
}
async function selectWorker(taskId, workerId) {
  const res = await fetch(API + "/tasks/" + taskId + "/select", {
    method: "POST",
    headers: headers(),
    body: JSON.stringify({ worker_id: workerId }),
  });
  const data = await res.json();
  if (res.ok) {
    say("Worker selected. Task is now in progress.", true);
    showTask(taskId);
  } else {
    say(JSON.stringify(data.errors || data.error), false);
  }
}


showView("quests");