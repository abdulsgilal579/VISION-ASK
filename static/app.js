const video = document.getElementById("video");
const canvas = document.getElementById("canvas");
const statusEl = document.getElementById("status");
const detectionsEl = document.getElementById("detections");
const answerEl = document.getElementById("answer");
const questionInput = document.getElementById("question");
const askBtn = document.getElementById("ask-btn");

let detectedObjects = [];

async function startCamera() {
    const stream = await navigator.mediaDevices.getUserMedia({ video: true });
    video.srcObject = stream;
    await new Promise((r) => (video.onloadedmetadata = r));
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    statusEl.textContent = "Camera ready — scanning every 2.5s";
    scanLoop();
}

async function scanLoop() {
    while (true) {
        await scan();
        await new Promise((r) => setTimeout(r, 2500));
    }
}

async function scan() {
    const ctx = canvas.getContext("2d");
    ctx.drawImage(video, 0, 0);
    const base64 = canvas.toDataURL("image/jpeg", 0.7).split(",")[1];

    statusEl.textContent = "Scanning...";
    try {
        const res = await fetch("/detect", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ image: base64 }),
        });
        const data = await res.json();
        detectedObjects = data.objects;
        renderDetections(detectedObjects);
        statusEl.textContent = `${detectedObjects.length} object(s) detected`;
    } catch {
        statusEl.textContent = "Detection error";
    }
}

function renderDetections(objects) {
    detectionsEl.innerHTML = objects
        .map(
            (o) =>
                `<span class="badge">${o.label} ${Math.round(o.confidence * 100)}%</span>`
        )
        .join("");
}

askBtn.addEventListener("click", async () => {
    const question = questionInput.value.trim();
    if (!question) return;

    askBtn.disabled = true;
    answerEl.textContent = "Thinking...";

    try {
        const res = await fetch("/ask", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ objects: detectedObjects, question }),
        });
        const data = await res.json();
        answerEl.textContent = data.answer;
    } catch {
        answerEl.textContent = "Error getting answer.";
    } finally {
        askBtn.disabled = false;
    }
});

questionInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") askBtn.click();
});

startCamera().catch((err) => {
    statusEl.textContent = "Camera error: " + err.message;
});
