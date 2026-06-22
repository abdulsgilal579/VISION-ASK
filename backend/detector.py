import cv2
import numpy as np
from ultralytics import YOLO

model = YOLO("yolov8n.pt")

CONFIDENCE_THRESHOLD = 0.4
MAX_MISSES = 3
IOU_THRESHOLD = 0.3


class KalmanTrack:
    _next_id = 0

    def __init__(self, bbox: list[float], label: str, confidence: float):
        self.id = KalmanTrack._next_id
        KalmanTrack._next_id += 1
        self.label = label
        self.confidence = confidence
        self.misses = 0
        self.prev_bbox: list[float] | None = None

        # State vector: [x, y, w, h, vx, vy, vw, vh]
        self.kf = cv2.KalmanFilter(8, 4)
        self.kf.measurementMatrix = np.eye(4, 8, dtype=np.float32)
        self.kf.transitionMatrix = np.eye(8, dtype=np.float32)
        for i in range(4):
            self.kf.transitionMatrix[i, i + 4] = 1.0
        self.kf.processNoiseCov = np.eye(8, dtype=np.float32) * 1e-2
        self.kf.measurementNoiseCov = np.eye(4, dtype=np.float32) * 1e-1
        self.kf.errorCovPost = np.eye(8, dtype=np.float32)
        self.kf.statePost = np.array(
            [*bbox, 0, 0, 0, 0], dtype=np.float32
        ).reshape(-1, 1)

    def predict(self) -> None:
        self.kf.predict()
        self.misses += 1

    def update(self, bbox: list[float], confidence: float) -> None:
        self.prev_bbox = self.bbox
        self.confidence = confidence
        self.misses = 0
        self.kf.correct(np.array(bbox, dtype=np.float32).reshape(-1, 1))

    @property
    def bbox(self) -> list[float]:
        return self.kf.statePost[:4].flatten().tolist()


def _iou(a: list[float], b: list[float]) -> float:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    ix = max(ax, bx)
    iy = max(ay, by)
    iw = max(0.0, min(ax + aw, bx + bw) - ix)
    ih = max(0.0, min(ay + ah, by + bh) - iy)
    intersection = iw * ih
    union = aw * ah + bw * bh - intersection
    return intersection / union if union > 0 else 0.0


class ObjectTracker:
    def __init__(self) -> None:
        self.tracks: list[KalmanTrack] = []

    def update(self, detections: list[dict]) -> list[dict]:
        for track in self.tracks:
            track.predict()

        matched_dets: set[int] = set()
        matched_tracks: set[int] = set()

        for d_idx, det in enumerate(detections):
            best_iou = IOU_THRESHOLD
            best_t_idx = None
            for t_idx, track in enumerate(self.tracks):
                if t_idx in matched_tracks or track.label != det["label"]:
                    continue
                score = _iou(det["bbox"], track.bbox)
                if score > best_iou:
                    best_iou = score
                    best_t_idx = t_idx
            if best_t_idx is not None:
                self.tracks[best_t_idx].update(det["bbox"], det["confidence"])
                matched_dets.add(d_idx)
                matched_tracks.add(best_t_idx)

        for d_idx, det in enumerate(detections):
            if d_idx not in matched_dets:
                self.tracks.append(KalmanTrack(det["bbox"], det["label"], det["confidence"]))

        self.tracks = [t for t in self.tracks if t.misses <= MAX_MISSES]

        return [
            {
                "label": t.label,
                "confidence": round(t.confidence, 2),
                "bbox": [round(v, 1) for v in t.bbox],
                "prev_bbox": [round(v, 1) for v in t.prev_bbox] if t.prev_bbox else None,
            }
            for t in self.tracks
        ]


_tracker = ObjectTracker()


def detect(image_bytes: bytes) -> list[dict]:
    arr = np.frombuffer(image_bytes, np.uint8)
    frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if frame is None:
        return []

    results = model(frame, verbose=False)[0]

    detections = []
    for box in results.boxes:
        conf = float(box.conf[0])
        if conf < CONFIDENCE_THRESHOLD:
            continue
        label = results.names[int(box.cls[0])]
        x1, y1, x2, y2 = box.xyxy[0].tolist()
        detections.append({"label": label, "confidence": conf, "bbox": [x1, y1, x2 - x1, y2 - y1]})

    return _tracker.update(detections)
