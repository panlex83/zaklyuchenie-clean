import base64
import os
import json
import re
from io import BytesIO
from PIL import Image
from openai import OpenAI

# Подключение по ключу из переменной окружения
client = OpenAI.api_key = os.getenv("OPENAI_API_KEY")

def encode_image(image_path):
    with Image.open(image_path) as img:
        buffered = BytesIO()
        img.save(buffered, format="JPEG")
        return base64.b64encode(buffered.getvalue()).decode("utf-8")

def clean_json_block(content: str) -> str:
    return re.sub(r"^```json|```$", "", content.strip(), flags=re.MULTILINE).strip()

def extract_structured_info_from_image(image_path: str, doc_type: str = 'id_card') -> dict:
    base64_img = encode_image(image_path)

    # Жёсткий prompt: без markdown, без пояснений, только JSON
    instruction = (
        "Ты — эксперт по распознаванию документов. "
        "Извлеки строго нужные поля из изображения документа."
        "Ответ верни строго в формате JSON. Без markdown, без ```json, без пояснений, без текста до или после. Только чистый JSON."
        "У удостоверения номер на оборотной стороне. У техпаспорта целевое владение подчеркнуто."
    )

    fields = (
        "- fio\n"
        "- id_number\n"
        "- id_date\n"
        if doc_type == "id_card" else
        "- address\n"
        "- cadastral_number\n"
        "- build_year\n"
        "- purpose"
    )

    example = (
        '{ "fio": "Иванов Иван Иванович", "id_number": "123456789", "id_date": "12.03.2020" }'
        if doc_type == "id_card" else
        '{ "address": "г. Алматы, ул. Ключевая, дом 14, кв. 3", "cadastral_number": "03-046-140-1757", "build_year": "2010", "purpose": "жилое" }'
    )

    prompt = (
        f"{instruction}\n\n"
        f"Если документ — удостоверение личности, поля:\n{fields}\n"
        f"Пример:\n{example}"
    )

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_img}"
                        },
                    },
                ],
            }
        ],
        max_tokens=700,
        temperature=0.2
    )

    content = response.choices[0].message.content.strip()
    print("\n=== RAW RESPONSE ===\n", content)

    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        print("⚠️ Ошибка при разборе JSON:", e)
        return {}
