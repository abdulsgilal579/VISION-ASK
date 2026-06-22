# VisionAsk

A real-time object-aware Q&A assistant. Point your webcam at a scene, ask a question in plain English, and get a grounded answer based on what is actually detected — including whether objects have moved between frames.

---

## What It Does

- Captures a webcam snapshot every 2.5 seconds
- Runs YOLOv8 nano object detection on each frame
- Tracks each detected object across frames using a Kalman filter
- Lets you type any natural language question about the scene
- Sends the detected objects (with positions and movement deltas) to Groq's LLaMA 3 LLM
- Returns a concise, grounded answer in under 300ms

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | HTML / CSS / Vanilla JS |
| Backend | Python, FastAPI |
| Object Detection | YOLOv8 nano (`yolov8n.pt`) via Ultralytics — 80 COCO classes, no custom training |
| Object Tracking | Kalman filter (OpenCV) with IoU-based multi-object association |
| LLM Inference | Groq API — `llama-3.3-70b-versatile` |
| Communication | HTTP (JSON) between frontend and backend |

---

## Project Structure

```
VisionAsk/
├── backend/
│   ├── __init__.py
│   ├── main.py        # FastAPI app — /detect and /ask endpoints, serves static/
│   ├── detector.py    # YOLOv8 inference + Kalman filter multi-object tracker
│   └── llm.py         # Groq API integration, prompt construction
├── static/
│   ├── index.html     # Webcam feed + Q&A interface
│   ├── style.css      # Dark theme layout
│   └── app.js         # getUserMedia, polling loop, fetch calls
├── scripts/
│   └── cameratest.py  # Standalone camera sanity check (OpenCV)
├── requirements.txt
├── .env               # GROQ_API_KEY (gitignored)
└── .gitignore
```

---

## Setup

**1. Clone and create a virtual environment**

```bash
git clone <repo-url>
cd VisionAsk
python3 -m venv venv
source venv/bin/activate
```

**2. Install dependencies**

```bash
pip install -r requirements.txt
pip install python-dotenv
```

**3. Add your Groq API key**

Create a `.env` file in the project root:

```
GROQ_API_KEY=your_key_here
```

Get a free key at [console.groq.com](https://console.groq.com).

**4. Run the server**

```bash
uvicorn backend.main:app --reload
```

Open `http://localhost:8000` in your browser.

---

## How It Works

### Detection Pipeline

Each frame goes through:

```
Webcam (getUserMedia)
  → canvas snapshot → base64 JPEG
  → POST /detect
  → YOLOv8 inference (80 COCO classes)
  → confidence filter (≥ 0.4)
  → Kalman filter tracker (IoU matching)
  → [{label, confidence, bbox, prev_bbox}]
  → detection badges on UI
```

### Tracking (Kalman Filter)

YOLO is stateless — it sees one frame at a time with no memory. The Kalman filter adds temporal continuity:

- Maintains one filter per tracked object with state `[x, y, w, h, vx, vy, vw, vh]`
- **Predict step:** estimates where each object will be before YOLO runs
- **Update step:** corrects the estimate using YOLO's actual detection (IoU matching)
- Stores `prev_bbox` before each update so movement can be measured
- Removes a track after 3 consecutive missed detections (`MAX_MISSES = 3`)

### Q&A Pipeline

```
User types question
  → POST /ask  {objects: [...], question: "..."}
  → llm.py builds structured prompt
  → Groq API (llama-3.3-70b-versatile)
  → answer displayed in UI
```

### What Gets Sent to the LLM

The prompt combines a system role with a structured scene description built from the tracker output. Example:

```
--- PROMPT ---
Detected objects:
- person (52%) at center (320.6, 251.5), previously at (333.7, 254.5), moved by (-13.1, -3.0) pixels

Question: what is the person doing
--------------
```

The `moved by` delta is only included when the same object has been tracked for at least two scans (≥ 5 seconds). On the first scan there is no previous position, so movement questions will correctly say the data is unavailable.

**System message sent to LLM:**
```
You are a visual assistant. You are given a list of objects detected in a live webcam 
scene along with their confidence scores. Answer the user's question based only on what 
is detected. Be concise. If the question is about movement, compare the current and 
previous positions if provided.
```

---

## API Reference

### `POST /detect`

Accepts a base64-encoded JPEG frame, returns tracked detections.

**Request**
```json
{ "image": "<base64_jpeg_string>" }
```

**Response**
```json
{
  "objects": [
    {
      "label": "person",
      "confidence": 0.52,
      "bbox": [198.3, 126.0, 244.6, 251.0],
      "prev_bbox": [211.4, 129.0, 244.6, 251.0]
    }
  ]
}
```

`bbox` format is `[x, y, width, height]` in pixels.

### `POST /ask`

Accepts the current object list and a question, returns an LLM answer.

**Request**
```json
{
  "objects": [{ "label": "person", "confidence": 0.52, "bbox": [...], "prev_bbox": [...] }],
  "question": "what is the person doing"
}
```

**Response**
```json
{ "answer": "The person appears to be moving slightly to the left based on the position change." }
```

---

## Camera Test

To verify your camera works before running the full app:

```bash
python scripts/cameratest.py
```

Press `Q` to quit.

---

## Notes

- YOLOv8n is the nano variant — fast but less accurate than larger models. Swap `yolov8n.pt` for `yolov8s.pt` or `yolov8m.pt` for better accuracy at the cost of speed.
- The Kalman filter tracks by label + IoU. Two objects of the same class close together may get cross-matched.
- Movement detection requires the object to be tracked for at least 2 scans (5 seconds) before `prev_bbox` is available.
- Groq's free tier has rate limits. If you hit them, the `/ask` endpoint will return a 500 error.
