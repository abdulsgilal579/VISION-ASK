import os

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

SYSTEM_PROMPT = (
    "You are a visual assistant. You are given a list of objects detected in a live webcam scene "
    "along with their confidence scores. Answer the user's question based only on what is detected. "
    "Be concise. If the question is about movement, compare the current and previous positions if provided."
)


def _describe_objects(objects: list[dict]) -> str:
    lines = []
    for o in objects:
        x, y, w, h = o["bbox"]
        center_x, center_y = round(x + w / 2, 1), round(y + h / 2, 1)
        line = f"- {o['label']} ({round(o['confidence'] * 100)}%) at center ({center_x}, {center_y})"
        if o.get("prev_bbox"):
            px, py, pw, ph = o["prev_bbox"]
            prev_cx, prev_cy = round(px + pw / 2, 1), round(py + ph / 2, 1)
            dx, dy = round(center_x - prev_cx, 1), round(center_y - prev_cy, 1)
            line += f", previously at ({prev_cx}, {prev_cy}), moved by ({dx}, {dy}) pixels"
        lines.append(line)
    return "\n".join(lines)


def ask(objects: list[dict], question: str) -> str:
    if not objects:
        scene = "No objects detected in the current scene."
    else:
        scene = f"Detected objects:\n{_describe_objects(objects)}"

    print(f"\n--- PROMPT ---\n{scene}\n\nQuestion: {question}\n--------------\n")
    response = _client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"{scene}\n\nQuestion: {question}"},
        ],
        max_tokens=300,
    )

    return response.choices[0].message.content
