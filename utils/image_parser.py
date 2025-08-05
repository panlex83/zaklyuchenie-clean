import easyocr
import re

reader = easyocr.Reader(['ru', 'en'], gpu=False)

def extract_relevant_data(image_path: str, doc_type: str) -> dict:
    result = reader.readtext(image_path, detail=0, paragraph=True)
    text = ' '.join(result).replace('\n', ' ').replace("  ", " ")
    data = {}

    if doc_type == 'id_card':
        # ФИО (по шаблону из текста: 3 слова подряд с заглавных букв)
        fio_match = re.search(r'([А-ЯЁ]{2,}\s+[А-ЯЁ]{2,}\s+[А-ЯЁ]{2,})', text)
        if fio_match:
            data['fio'] = fio_match.group(1)

        # Номер и дата удостоверения
        num_date_match = re.search(r'(ID|№|N)?\s?(\d{9,})[^0-9]*(\d{2}\.\d{2}\.\d{4})', text)
        if num_date_match:
            data['id_number_date'] = f"{num_date_match.group(2)} от {num_date_match.group(3)}"

    elif doc_type == 'passport':
        # Адрес: ищем строку с ул., дом, кв.
        address_match = re.search(r'(ул|улица)\.?\s[А-Яа-яёЁ0-9,\s\-]+д[оа]м\s*\d+[^\n,]*', text)
        if not address_match:
            address_match = re.search(r'Адрес\s+([^\n\r]+)', text, re.IGNORECASE)
        if address_match:
            data['address'] = address_match.group(0)

        # Кадастровый номер
        cadastral_match = re.search(r'\d{2}-+\d{3}-\d{3}-\d{4}', text)
        if cadastral_match:
            data['cadastral_number'] = cadastral_match.group(0)

        # Год постройки
        year_match = re.search(r'(19|20)\d{2}', text)
        if year_match:
            data['build_year'] = year_match.group(0)

        # Назначение: частный дом / дача / гараж
        if "частн" in text.lower():
            data['purpose'] = "частный дом"
        elif "дач" in text.lower():
            data['purpose'] = "дача"
        elif "гараж" in text.lower():
            data['purpose'] = "гараж"
        else:
            data['purpose'] = "иное"

    return data
