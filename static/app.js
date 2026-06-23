const video = document.getElementById("video");
const canvas = document.getElementById("canvas");
const statusEl = document.getElementById("status");
const detectionsEl = document.getElementById("detections");
const chatLog = document.getElementById("chat-log");
const questionInput = document.getElementById("question");
const askBtn = document.getElementById("ask-btn");

let detectedObjects = [];

async function startCamera() {
    const stream = await navigator.mediaDevices.getUserMedia({ video: true });
    video.srcObject = stream;
    await new Promise((r) => (video.onloadedmetadata = r));
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    statusEl.textContent = "Live · scanning every 2.5s";
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

    try {
        const res = await fetch("/detect", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ image: base64 }),
        });
        const data = await res.json();
        detectedObjects = data.objects;
        renderDetections(detectedObjects);
        statusEl.textContent = `Live · ${detectedObjects.length} object(s) detected`;
    } catch {
        statusEl.textContent = "Detection error";
    }
}

function renderDetections(objects) {
    if (objects.length === 0) {
        detectionsEl.innerHTML = `<span style="font-size:0.75rem;color:#4a5568;">Nothing detected</span>`;
        return;
    }
    detectionsEl.innerHTML = objects
        .map((o) => `<span class="badge">${o.label} ${Math.round(o.confidence * 100)}%</span>`)
        .join("");
}

function captureFrame() {
    const ctx = canvas.getContext("2d");
    ctx.drawImage(video, 0, 0);
    return canvas.toDataURL("image/jpeg", 0.7).split(",")[1];
}

function appendMessage(role, text) {
    const empty = chatLog.querySelector(".chat-empty");
    if (empty) empty.remove();

    const row = document.createElement("div");
    row.className = `chat-row ${role}`;

    const avatar = document.createElement("div");
    avatar.className = "avatar";
    avatar.textContent = role === "user" ? "Y" : "👁";

    const col = document.createElement("div");
    col.className = "bubble-col";

    const name = document.createElement("span");
    name.className = "bubble-name";
    name.textContent = role === "user" ? "You" : "VisionAsk";

    const bubble = document.createElement("div");
    bubble.className = "chat-bubble";
    bubble.textContent = text;

    col.appendChild(name);
    col.appendChild(bubble);
    row.appendChild(avatar);
    row.appendChild(col);
    chatLog.appendChild(row);
    chatLog.scrollTop = chatLog.scrollHeight;

    return bubble;
}

function appendThinking() {
    const empty = chatLog.querySelector(".chat-empty");
    if (empty) empty.remove();

    const row = document.createElement("div");
    row.className = "chat-row assistant";

    const avatar = document.createElement("div");
    avatar.className = "avatar";
    avatar.textContent = "👁";

    const col = document.createElement("div");
    col.className = "bubble-col";

    const name = document.createElement("span");
    name.className = "bubble-name";
    name.textContent = "VisionAsk";

    const bubble = document.createElement("div");
    bubble.className = "chat-bubble";
    bubble.innerHTML = `<div class="thinking-dots"><span></span><span></span><span></span></div>`;

    col.appendChild(name);
    col.appendChild(bubble);
    row.appendChild(avatar);
    row.appendChild(col);
    chatLog.appendChild(row);
    chatLog.scrollTop = chatLog.scrollHeight;

    return { row, bubble };
}

askBtn.addEventListener("click", async () => {
    const question = questionInput.value.trim();
    if (!question) return;

    askBtn.disabled = true;
    questionInput.value = "";

    appendMessage("user", question);
    const { row: thinkingRow, bubble: thinkingBubble } = appendThinking();

    const image = captureFrame();

    try {
        const res = await fetch("/ask", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ objects: detectedObjects, question, image }),
        });
        const data = await res.json();
        thinkingBubble.textContent = data.answer;
    } catch {
        thinkingBubble.textContent = "Something went wrong. Please try again.";
    } finally {
        askBtn.disabled = false;
        chatLog.scrollTop = chatLog.scrollHeight;
    }
});

questionInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") askBtn.click();
});

startCamera().catch((err) => {
    statusEl.textContent = "Camera error: " + err.message;
});
