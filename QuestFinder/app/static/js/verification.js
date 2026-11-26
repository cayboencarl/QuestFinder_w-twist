/* QuestFinder — identity verification: ID scan → live face scan → face match → submit.
 *
 * Face matching runs in the browser with face-api (TensorFlow.js). Each face is
 * turned into a 128-number descriptor; the Euclidean distance between the ID
 * face and the live face is the match score (lower = more alike). The server
 * re-checks the score against FACE_MATCH_THRESHOLD and the Barangay Admin makes
 * the final decision by comparing the two images.
 */
(function () {
  "use strict";
  const app = document.getElementById("verifyApp");
  if (!app || !window.faceapi) return;

  const $ = (id) => document.getElementById(id);
  const THRESHOLD = parseFloat(app.dataset.threshold) || 0.55;
  const MIN_AGE = 18;

  const state = {
    modelsReady: false,
    idBlob: null, idDescriptor: null,
    faceBlob: null, faceDistance: null,
    stream: null,
  };

  // ---------------------------------------------------------------- helpers
  function setMsg(el, text, kind) {
    el.textContent = text || "";
    el.className = "scan-msg" + (kind ? " scan-" + kind : "");
  }

  function showStep(n) {
    document.querySelectorAll("[data-step]").forEach((s) => (s.hidden = s.dataset.step !== String(n)));
    document.querySelectorAll("[data-step-dot]").forEach((d) => {
      const k = Number(d.dataset.stepDot);
      d.classList.toggle("active", k === n);
      d.classList.toggle("done", k < n);
    });
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function stopCamera() {
    if (state.stream) state.stream.getTracks().forEach((t) => t.stop());
    state.stream = null;
  }

  async function startCamera(video, facingMode) {
    stopCamera();
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      throw new Error("This browser cannot open the camera. Use Chrome on your phone, or upload a photo of your ID.");
    }
    state.stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: { ideal: facingMode }, width: { ideal: 1280 }, height: { ideal: 720 } },
      audio: false,
    });
    video.srcObject = state.stream;
    video.hidden = false;
    await video.play();
  }

  function frameToCanvas(source, mirror) {
    const w = source.videoWidth || source.naturalWidth;
    const h = source.videoHeight || source.naturalHeight;
    const c = document.createElement("canvas");
    c.width = w; c.height = h;
    const ctx = c.getContext("2d");
    if (mirror) { ctx.translate(w, 0); ctx.scale(-1, 1); }
    ctx.drawImage(source, 0, 0, w, h);
    return c;
  }

  const canvasToBlob = (c) => new Promise((res) => c.toBlob(res, "image/jpeg", 0.9));

  function ageOn(birth, today) {
    let age = today.getFullYear() - birth.getFullYear();
    const m = today.getMonth() - birth.getMonth();
    if (m < 0 || (m === 0 && today.getDate() < birth.getDate())) age--;
    return age;
  }

  // ---------------------------------------------------------------- models
  async function loadModels() {
    const url = app.dataset.models;
    try {
      await Promise.all([
        faceapi.nets.ssdMobilenetv1.loadFromUri(url),
        faceapi.nets.faceLandmark68Net.loadFromUri(url),
        faceapi.nets.faceRecognitionNet.loadFromUri(url),
      ]);
      state.modelsReady = true;
      setMsg($("modelStatus"), "Face scanner ready.", "ok");
    } catch (err) {
      console.error(err);
      setMsg($("modelStatus"), "Could not load the face scanner. Check your connection and reload the page.", "error");
    }
  }

  async function bestFace(input, minConfidence) {
    const options = new faceapi.SsdMobilenetv1Options({ minConfidence });
    const faces = await faceapi.detectAllFaces(input, options).withFaceLandmarks().withFaceDescriptors();
    if (!faces.length) return { face: null, count: 0 };
    // On IDs there may be a small "ghost" photo; use the largest face.
    faces.sort((a, b) => b.detection.box.area - a.detection.box.area);
    return { face: faces[0], count: faces.length };
  }

  // ---------------------------------------------------------------- step 1: ID
  async function handleIdImage(canvasOrImg) {
    const msg = $("idMsg");
    if (!state.modelsReady) { setMsg(msg, "Please wait, the face scanner is still loading…", "warn"); return; }
    setMsg(msg, "Looking for the photo on your ID…");
    const { face } = await bestFace(canvasOrImg, 0.3);
    if (!face) {
      state.idDescriptor = null;
      setMsg(msg, "We couldn't find the photo on your ID. Retake it closer, in good light, without glare.", "error");
    } else {
      state.idDescriptor = face.descriptor;
      setMsg(msg, "ID photo found ✓", "ok");
    }
    validateStep1();
  }

  $("idCameraBtn").addEventListener("click", async () => {
    try {
      await startCamera($("idVideo"), "environment");
      $("idPreview").hidden = true; $("idEmpty").hidden = true; $("idGuide").hidden = false;
      $("idCaptureBtn").hidden = false;
      setMsg($("idMsg"), "Fit your whole ID inside the frame, then tap Capture ID.");
    } catch (err) {
      setMsg($("idMsg"), cameraError(err), "error");
    }
  });

  $("idCaptureBtn").addEventListener("click", async () => {
    const video = $("idVideo");
    const canvas = frameToCanvas(video, false);
    stopCamera();
    video.hidden = true; $("idGuide").hidden = true; $("idCaptureBtn").hidden = true;
    state.idBlob = await canvasToBlob(canvas);
    $("idPreview").src = URL.createObjectURL(state.idBlob);
    $("idPreview").hidden = false;
    $("idCameraBtn").textContent = "Retake";
    await handleIdImage(canvas);
  });

  $("idFile").addEventListener("change", async (e) => {
    const file = e.target.files && e.target.files[0];
    if (!file) return;
    if (!/^image\//.test(file.type)) { setMsg($("idMsg"), "Choose an image file.", "error"); return; }
    stopCamera();
    $("idVideo").hidden = true; $("idGuide").hidden = true; $("idCaptureBtn").hidden = true; $("idEmpty").hidden = true;
    const img = $("idPreview");
    img.src = URL.createObjectURL(file);
    img.hidden = false;
    await img.decode();
    state.idBlob = await canvasToBlob(frameToCanvas(img, false));
    await handleIdImage(img);
  });

  function step1Errors() {
    if (!state.idBlob) return "Scan your ID first.";
    if (!state.idDescriptor) return "The photo on your ID must be visible.";
    if (!$("idType").value) return "Choose the type of ID.";
    if ($("idNumber").value.replace(/[^A-Za-z0-9]/g, "").length < 4) return "Enter the ID number.";
    if ($("nameOnId").value.trim().length < 3) return "Enter your full name as printed on the ID.";
    const b = $("birthdateOnId").value;
    if (!b) return "Enter the birthdate on your ID.";
    if (ageOn(new Date(b + "T00:00:00"), new Date()) < MIN_AGE) return "QuestFinder is strictly for users 18 years old and above.";
    return null;
  }

  function validateStep1() {
    const err = step1Errors();
    $("toStep2").disabled = !!err;
    $("toStep2").title = err || "";
    const b = $("birthdateOnId").value;
    if (b && ageOn(new Date(b + "T00:00:00"), new Date()) < MIN_AGE) {
      setMsg($("idMsg"), "QuestFinder is strictly for users 18 years old and above.", "error");
    }
  }
  ["idType", "idNumber", "nameOnId", "birthdateOnId"].forEach((id) => {
    $(id).addEventListener("input", validateStep1);
    $(id).addEventListener("change", validateStep1);
  });

  $("toStep2").addEventListener("click", async () => {
    if (step1Errors()) return;
    showStep(2);
    try {
      await startCamera($("faceVideo"), "user");
      $("faceScanBtn").disabled = !state.modelsReady;
      setMsg($("faceMsg"), "Keep your face inside the oval, then tap Scan my face.");
    } catch (err) {
      setMsg($("faceMsg"), cameraError(err), "error");
    }
  });

  // ---------------------------------------------------------------- step 2: face
  $("faceScanBtn").addEventListener("click", async () => {
    const btn = $("faceScanBtn");
    const video = $("faceVideo");
    btn.disabled = true;
    $("matchResult").hidden = true;
    setMsg($("faceMsg"), "Scanning… hold still.");

    // Take 3 frames over ~1.5 s. Each must show exactly one face; their
    // descriptors are averaged for a steadier result.
    const descriptors = [];
    let lastCanvas = null;
    for (let i = 0; i < 3; i++) {
      const canvas = frameToCanvas(video, false); // not mirrored: must match the ID orientation
      const { face, count } = await bestFace(canvas, 0.5);
      if (count > 1) { setMsg($("faceMsg"), "Only one person should be in front of the camera.", "error"); btn.disabled = false; return; }
      if (!face) { setMsg($("faceMsg"), "No face found. Move closer, face the light, and try again.", "error"); btn.disabled = false; return; }
      descriptors.push(face.descriptor);
      lastCanvas = canvas;
      await new Promise((r) => setTimeout(r, 500));
    }
    const avg = new Float32Array(128);
    descriptors.forEach((d) => d.forEach((v, i) => (avg[i] += v / descriptors.length)));
    const distance = faceapi.euclideanDistance(avg, state.idDescriptor);

    state.faceBlob = await canvasToBlob(lastCanvas);
    state.faceDistance = distance;
    const similarity = Math.max(0, Math.round((1 - distance) * 100));
    const passed = distance <= THRESHOLD;

    const box = $("matchResult");
    box.hidden = false;
    box.className = "match-result " + (passed ? "match-ok" : "match-fail");
    box.innerHTML = passed
      ? `<strong>Face matches your ID ✓</strong><span>Similarity ${similarity}%</span>`
      : `<strong>Face does not match your ID</strong><span>Similarity ${similarity}%. Try again with better light, or retake your ID scan.</span>`;
    setMsg($("faceMsg"), "");
    $("toStep3").disabled = !passed;
    btn.disabled = false;
    btn.textContent = "Scan again";
  });

  $("backToStep1").addEventListener("click", () => { stopCamera(); showStep(1); });

  // ---------------------------------------------------------------- step 3: submit
  $("toStep3").addEventListener("click", () => {
    stopCamera();
    $("reviewId").src = URL.createObjectURL(state.idBlob);
    $("reviewFace").src = URL.createObjectURL(state.faceBlob);
    const idType = $("idType");
    const num = $("idNumber").value.replace(/[^A-Za-z0-9]/g, "");
    $("reviewDetails").innerHTML =
      `<dt>ID</dt><dd>${QF.escape(idType.options[idType.selectedIndex].text)} ••••${QF.escape(num.slice(-4))}</dd>` +
      `<dt>Name</dt><dd>${QF.escape($("nameOnId").value.trim())}</dd>` +
      `<dt>Birthdate</dt><dd>${QF.escape($("birthdateOnId").value)}</dd>` +
      `<dt>Face match</dt><dd>${Math.max(0, Math.round((1 - state.faceDistance) * 100))}% ✓</dd>`;
    showStep(3);
  });

  $("backToStep2").addEventListener("click", async () => {
    showStep(2);
    try { await startCamera($("faceVideo"), "user"); } catch (err) { setMsg($("faceMsg"), cameraError(err), "error"); }
  });

  $("confirmTrue").addEventListener("change", (e) => ($("submitBtn").disabled = !e.target.checked));

  $("submitBtn").addEventListener("click", async () => {
    const btn = $("submitBtn");
    btn.disabled = true;
    setMsg($("submitMsg"), "Sending to the Barangay Admin…");
    const data = new FormData();
    data.append("id_type", $("idType").value);
    data.append("id_number", $("idNumber").value);
    data.append("name_on_id", $("nameOnId").value);
    data.append("birthdate_on_id", $("birthdateOnId").value);
    data.append("face_distance", String(state.faceDistance));
    data.append("id_image", state.idBlob, "id.jpg");
    data.append("face_image", state.faceBlob, "face.jpg");
    try {
      const res = await QF.fetchJSON(app.dataset.submit, { method: "POST", body: data });
      window.location.href = res.redirect;
    } catch (err) {
      setMsg($("submitMsg"), err.message, "error");
      btn.disabled = false;
    }
  });

  function cameraError(err) {
    if (err && (err.name === "NotAllowedError" || err.name === "SecurityError")) {
      return "Camera permission was blocked. Allow camera access in your browser settings, then try again.";
    }
    if (err && err.name === "NotFoundError") return "No camera was found on this device.";
    return (err && err.message) || "Could not open the camera.";
  }

  window.addEventListener("pagehide", stopCamera);
  loadModels();
})();
