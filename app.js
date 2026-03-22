const photoLayer = document.getElementById("photoLayer");
const digitalClock = document.getElementById("digitalClock");
const statusText = document.getElementById("status");
const canvas = document.getElementById("clockCanvas");
const ctx = canvas.getContext("2d");

const state = {
  defaultPhoto: "",
  showAnalog: true,
  mode24: true,
  rotation: "portrait"
};

let lastPhotoUrl = "";
let lastFetchSignature = "";
let lastSecondDrawn = -1;
let loadFailed = false;

function resizeCanvas() {
  const dpr = window.devicePixelRatio || 1;
  const stage = document.getElementById("stage");
  const rect = stage.getBoundingClientRect();
  canvas.width = Math.round(rect.width * dpr);
  canvas.height = Math.round(rect.height * dpr);
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.scale(dpr, dpr);
}

function formatTime(date, mode24) {
  if (mode24) return date.toLocaleTimeString([], { hour12: false });
  return date.toLocaleTimeString([], { hour12: true });
}

function drawHand(cx, cy, length, width, angle, color) {
  ctx.save();
  ctx.translate(cx, cy);
  ctx.rotate(angle);
  ctx.beginPath();
  ctx.moveTo(0, 10);
  ctx.lineTo(0, -length);
  ctx.lineWidth = width;
  ctx.lineCap = "round";
  ctx.strokeStyle = color;
  ctx.shadowColor = color;
  ctx.shadowBlur = Math.max(6, width * 2);
  ctx.stroke();
  ctx.restore();
}

function drawAnalogClock(now) {
  if (!state.showAnalog) return;

  const stage = document.getElementById("stage");
  const rect = stage.getBoundingClientRect();
  const w = rect.width;
  const h = rect.height;
  const cx = w / 2;
  const cy = h * 0.39;
  const radius = Math.min(w, h) * 0.22;

  ctx.beginPath();
  ctx.arc(cx, cy, radius, 0, Math.PI * 2);
  ctx.lineWidth = 5;
  ctx.strokeStyle = "rgba(255, 246, 234, 0.78)";
  ctx.shadowColor = "rgba(0, 0, 0, 0.24)";
  ctx.shadowBlur = 16;
  ctx.stroke();

  for (let i = 0; i < 12; i += 1) {
    const angle = (Math.PI * 2 * i) / 12;
    const x1 = cx + Math.sin(angle) * radius * 0.8;
    const y1 = cy - Math.cos(angle) * radius * 0.8;
    const x2 = cx + Math.sin(angle) * radius * 0.94;
    const y2 = cy - Math.cos(angle) * radius * 0.94;
    ctx.beginPath();
    ctx.moveTo(x1, y1);
    ctx.lineTo(x2, y2);
    ctx.lineWidth = 4;
    ctx.strokeStyle = "rgba(255,255,255,0.88)";
    ctx.stroke();
  }

  const seconds = now.getSeconds() + now.getMilliseconds() / 1000;
  const minutes = now.getMinutes() + seconds / 60;
  const hours = (now.getHours() % 12) + minutes / 60;

  drawHand(cx, cy, radius * 0.48, 8, (Math.PI * 2 * hours) / 12, "rgba(255,255,255,0.95)");
  drawHand(cx, cy, radius * 0.7, 5, (Math.PI * 2 * minutes) / 60, "rgba(245,240,255,0.92)");
  drawHand(cx, cy, radius * 0.84, 3, (Math.PI * 2 * seconds) / 60, "rgba(255,132,122,0.95)");

  ctx.beginPath();
  ctx.arc(cx, cy, 7, 0, Math.PI * 2);
  ctx.fillStyle = "white";
  ctx.fill();
}

function applyRotation() {
  const classes = ["rotate-portrait", "rotate-portrait-flipped", "rotate-landscape-flipped"];
  document.body.classList.remove(...classes);
  if (state.rotation === "portrait" && window.innerWidth > window.innerHeight) {
    document.body.classList.add("rotate-portrait");
  } else if (state.rotation === "portrait-flipped" && window.innerWidth > window.innerHeight) {
    document.body.classList.add("rotate-portrait-flipped");
  } else if (state.rotation === "landscape-flipped") {
    document.body.classList.add("rotate-landscape-flipped");
  } else if (state.rotation === "portrait-flipped") {
    document.body.classList.add("rotate-landscape-flipped");
  }
  resizeCanvas();
}

function applyState(nextState) {
  state.defaultPhoto = nextState.defaultPhoto || "";
  state.showAnalog = nextState.showAnalog !== false;
  state.mode24 = nextState.mode24 !== false;
  state.rotation = nextState.rotation || "portrait";

  applyRotation();

  if (state.defaultPhoto && lastPhotoUrl !== state.defaultPhoto) {
    photoLayer.src = `${state.defaultPhoto}${state.defaultPhoto.includes("?") ? "&" : "?"}ts=${Date.now()}`;
    lastPhotoUrl = state.defaultPhoto;
  }

  statusText.style.display = state.defaultPhoto ? "none" : "block";
  statusText.textContent = state.defaultPhoto ? "" : "No default photo selected.";
  loadFailed = false;
}

async function refreshState() {
  try {
    const response = await fetch("/api/state", { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const payload = await response.json();
    const signature = JSON.stringify(payload.state);
    if (signature !== lastFetchSignature) {
      applyState(payload.state);
      lastFetchSignature = signature;
    }
  } catch {
    statusText.style.display = "block";
    statusText.textContent = "Cannot reach clock server.";
  }
}

function render() {
  const now = new Date();
  if (now.getSeconds() !== lastSecondDrawn) {
    digitalClock.textContent = formatTime(now, state.mode24);
    lastSecondDrawn = now.getSeconds();
  }

  const stage = document.getElementById("stage");
  const rect = stage.getBoundingClientRect();
  ctx.clearRect(0, 0, rect.width, rect.height);
  drawAnalogClock(now);
  window.setTimeout(render, 125);
}

photoLayer.addEventListener("error", () => {
  if (loadFailed) return;
  loadFailed = true;
  statusText.style.display = "block";
  statusText.textContent = "Could not load selected photo.";
});

window.addEventListener("resize", applyRotation);

resizeCanvas();
refreshState();
window.setInterval(refreshState, 5000);
render();
