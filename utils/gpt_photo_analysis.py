import base64
import json
import os
import re
from io import BytesIO
from PIL import Image
from openai import OpenAI

client = OpenAI.api_key = os.getenv("OPENAI_API_KEY")

def encode_image(image_path: str) -> str:
    with Image.open(image_path) as img:
        buf = BytesIO()
        img.save(buf, format="JPEG")
        return base64.b64encode(buf.getvalue()).decode("utf-8")

def analyze_photo(image_path: str, element_name: str) -> str:
    b64 = encode_image(image_path)
    prompt = (
        f"Посмотри на фото элемента: {element_name}. "
        "Опиши его техническое состояние: наличие трещин, коррозии, повреждений. "
        "Верни только текст, без JSON, кратко, в одном предложении."
    )
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}" }}
            ]
        }],
        max_tokens=200,
        temperature=0.2
    )
    return response.choices[0].message.content.strip()

def analyze_photos(data: dict) -> dict:
    # пример элементов: foundation, walls, roof, windows
    result = {}
    for key, label in [
        ("foundation", "Фундамент"),
        ("walls", "Стены"),
        ("roof", "Кровля"),
        ("windows", "Окна и двери")
    ]:
        path = data.get(key)
        if path and os.path.exists(path):
            result[key] = analyze_photo(path, label)
        else:
            result[key] = "Фото не предоставлено"
    return result
