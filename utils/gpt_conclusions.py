# utils/gpt_conclusions.py

import os
import json
from typing import Any, Mapping
from openai import OpenAI

client = OpenAI.api_key = os.getenv("OPENAI_API_KEY")


def _format_defects(defects: Any) -> str:
    """
    Приводит поле defects к читабельной строке.
    Если передан список — соединяет элементы через '; ',
    если строка — возвращает как есть, в остальных случаях возвращает '—'.
    """
    if isinstance(defects, list):
        items = [str(d).strip() for d in defects if d]
        return "; ".join(items) or "—"
    elif isinstance(defects, str):
        return defects.strip() or "—"
    return "—"


def generate_conclusions(data: Mapping[str, Any]) -> Mapping[str, str]:
    """
    На основе анализа конструктивных элементов формирует:
      - overall_state: Категория V (аварийное состояние конструкции), неудовлетворительному, удовлетворительному, категория сложности X 
      - defects: перечень дефектов
      - recommendations: технические рекомендации

    Возвращает словарь с ключами above. Если GPT-ответ невалидный — возвращает понятные default-значения.
    """

    analysis = data.get("analysis", {})
    element_labels = data.get("element_labels", {})

    # Сбор краткого summary и списка дефектов
    summary = []
    defects = []
    for key, items in analysis.items():
        label = element_labels.get(key, key.capitalize())
        for obj in items or []:
            idx = obj.get("index", "?")
            desc = obj.get("description", "").strip()
            summary.append(f"{label} (фото {idx}): {desc}")
            defs = _format_defects(obj.get("defects"))
            if defs != "—":
                defects.append(f"{label}: {defs}")

    analysis_text = "\n".join(summary)

    # Если нет анализа — сразу наследуем дефолт
    if not analysis_text:
        return {
            "overall_state": "не определено (нет данных анализа)",
            "defects": "—",
            "recommendations": "нет данных для рекомендаций"
        }

    # Prompt для GPT — жёстко требуем чистый JSON без объяснений
    system_msg = (
        "Ты — эксперт по техническому обследованию зданий. На вход подаётся результат "
        "анализов конструктивных элементов объекта недвижимости, сформируй по ним "
        "финальные технические выводы и рекомендации. "
        "Отвечай строго JSON-объектом, **без** markdown, без описаний, без текста до/после."
    )

    user_msg = (
        f"Результаты анализа:\n{analysis_text}\n\n"
        "Формат JSON:\n"
        "- overall_state: 'Категория V (аварийное состояние конструкции), неудовлетворительному, удовлетворительному, категория сложности X'\n"
        "- defects: список дефектов или пустая строка\n"
        "- recommendations: требования/рекомендации\n\n"
        "Пример:\n"
        '{"overall_state":"удовлетворительное, категория сложности 1",'
        '"defects":"трещины на стене; повреждение кровли",'
        '"recommendations":"устранить трещины, проверить кровлю"}'
    )

    try:
        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg}
            ],
            temperature=0.0,
            max_tokens=400,
            top_p=1.0
        )
        raw = resp.choices[0].message.content.strip()

        # Удаляем возможные обрамления ```json``` или "`"
        cleaned = raw.strip("`")
        data_json = json.loads(cleaned)

        return {
            "overall_state": data_json.get("overall_state", "—"),
            "defects": data_json.get("defects", "—"),
            "recommendations": data_json.get("recommendations", "—")
        }

    except (json.JSONDecodeError, ValueError) as ex:
        # Optionally: лог raw здесь
        return {
            "overall_state": "ошибка при генерации заключения",
            "defects": "Не удалось распознать дефекты",
            "recommendations": "Не удалось составить рекомендации"
        }
    except Exception:
        return {
            "overall_state": "ошибка при генерации",
            "defects": "—",
            "recommendations": "—"
        }
