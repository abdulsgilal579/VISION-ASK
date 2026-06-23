import os
from typing import Optional

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

SYSTEM_PROMPT = (
    "You are a visual assistant analyzing a live webcam frame. "
    "Answer the user's question based on what you see in the image. "
    "Be concise and direct."
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


def ask(objects: list[dict], question: str, image_b64: Optional[str] = None) -> str:
    context_lines = []
    if objects:
        context_lines.append(f"Object tracker also detected:\n{_describe_objects(objects)}")

    context = "\n".join(context_lines)
    user_text = f"{context}\n\nQuestion: {question}".strip() if context else f"Question: {question}"

    if image_b64:
        user_content = [
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"},
            },
            {"type": "text", "text": user_text},
        ]
        model = "meta-llama/llama-4-scout-17b-16e-instruct"
    else:
        user_content = user_text
        model = "llama-3.3-70b-versatile"

    print(f"\n--- PROMPT ---\n{user_text}\nmodel={model}\n--------------\n")
    response = _client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        max_tokens=300,
    )

    return response.choices[0].message.content
