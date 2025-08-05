# utils/gpt_photo_analysis_batch.py

import os
import base64
import json
import re
from io import BytesIO
from PIL import Image
from openai import OpenAI

# Обязательно передай свой ключ через env-переменную OPENAI_API_KEY
client = OpenAI.api_key = os.getenv("OPENAI_API_KEY")

def encode_image(path: str) -> str:
    with Image.open(path) as img:
        buf = BytesIO()
        img.save(buf, format="JPEG")
        return base64.b64encode(buf.getvalue()).decode("utf-8")

def analyze_photos_batch(paths: list, element_name: str) -> list:
    prompt = (
        f"Анализируй {len(paths)} фото элемента \"{element_name}\".\n"
        "Для каждого фото в порядке отправки верни JSON-объект с полями:\n"
        "- index: номер (с 0)\n"
        "- description: краткое описание состояния\n"
        "- defects: обнаруженные дефекты\n"
        "- overall_state: Категория V (аварийное состояние конструкции), неудовлетворительное, удовлетворительное\n"
        "ОТВЕТЬ ТОЛЬКО JSON-МАССИВОМ, БЕЗ ОБЪЯСНЕНИЙ, БЕЗ ТЕКСТА ДО/ПОСЛЕ.\n"
        "Пример ответа:\n"
        '[{"index":0,"description":"...","defects":"...","overall_state":"..."}]'
    )

    messages = [{
        "role": "user",
        "content": [
            {"type": "text", "text": prompt},
        ] + [
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encode_image(p)}"}}
            for p in paths
        ]
    }]

    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        max_tokens=800,
        temperature=0.2
    )

    raw = resp.choices[0].message.content.strip()
    # Очистка Markdown-кода и символов «```json» перед JSON
    cleaned = re.sub(r"^```json|```$", "", raw.strip())
    cleaned = cleaned.strip()
    # Иногда OpenAI добавляет трейсинг или подпись — отрезаем лишнее после последней скобки
    if cleaned.endswith("}") and cleaned.count("[") and cleaned.count("]"):
        cleaned = cleaned[: cleaned.rfind("]") + 1 ]

    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, list):
            return parsed
    except json.JSONDecodeError as e:
        print("JSON‑парсинг не удалось:", e, "-> raw:", repr(raw), "-> cleaned:", repr(cleaned))

    # fallback возврат — список пуст
    return []
