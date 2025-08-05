import os
import logging
from telegram import Update
from telegram.ext import ContextTypes
from utils.doc_generator import generate_doc
from utils.extract_via_gpt import extract_structured_info_from_image

user_data = {}
current_step = {}
END = -1

QUESTIONS = [
    "Загрузите фото удостоверения личности",
    "Загрузите фото техпаспорта",
    "Загрузите фото фасада",
    "Загрузите фото фундамента",
    "Загрузите фото стен",
    "Загрузите фото крыши",
    "Загрузите фото окон и дверей"
]

PHOTO_KEYS = {
    0: "id_card",
    1: "passport",
    2: "facade",
    3: "foundation",
    4: "walls",
    5: "roof",
    6: "windows",
}

async def start_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data[user_id] = {}
    current_step[user_id] = 0

    await update.message.reply_text("Здравствуйте! Загрузите, пожалуйста, фото документов.")
    await update.message.reply_text(QUESTIONS[0])
    return 1

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    step = current_step.get(user_id)
    key = PHOTO_KEYS.get(step)

    try:
        photo_file = await update.message.photo[-1].get_file()
        os.makedirs("temp", exist_ok=True)

        # Поддержка нескольких фото
        user_photos = user_data[user_id].get(key, [])
        if not isinstance(user_photos, list):
            user_photos = [user_photos] if user_photos else []

        photo_path = f"temp/{user_id}_{key}_{len(user_photos) + 1}.jpg"
        await photo_file.download_to_drive(photo_path)
        user_photos.append(photo_path)
        user_data[user_id][key] = user_photos

        # Автоматическое GPT-распознавание только при первом документе
        if key == "id_card" and len(user_photos) == 1:
            gpt_data = extract_structured_info_from_image(photo_path, doc_type="id_card")
            await update.message.reply_text(f"Распознано: {gpt_data}")
            user_data[user_id]["full_name"] = gpt_data.get("fio")
            user_data[user_id]["id_number"] = gpt_data.get("id_number")
            user_data[user_id]["id_date"] = gpt_data.get("id_date")

        elif key == "passport" and len(user_photos) == 1:
            gpt_data = extract_structured_info_from_image(photo_path, doc_type="passport")
            await update.message.reply_text(f"Распознано: {gpt_data}")
            user_data[user_id]["address"] = gpt_data.get("address")
            user_data[user_id]["cadastral_number"] = gpt_data.get("cadastral_number")
            user_data[user_id]["build_year"] = gpt_data.get("build_year")
            user_data[user_id]["purpose"] = gpt_data.get("purpose")

        await update.message.reply_text("Если у вас есть ещё фото этого элемента — отправьте. Или нажмите /skip чтобы перейти к следующему шагу.")
        return 1

    except Exception as e:
        logging.exception(f"Ошибка у пользователя {user_id}: {str(e)}")
        await update.message.reply_text("Ошибка при обработке фото. Попробуйте снова или нажмите /cancel.")
        return 1

async def handle_skip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    step = current_step.get(user_id)
    current_step[user_id] += 1

    if current_step[user_id] < len(QUESTIONS):
        await update.message.reply_text(QUESTIONS[current_step[user_id]])
        return 1

    await update.message.reply_text("Все шаги завершены. Генерирую заключение...")

    # Генерация Word-файла
    path = generate_doc(user_data[user_id])
    await update.message.reply_document(document=open(path, "rb"))

    # Очистка
    user_data.pop(user_id, None)
    current_step.pop(user_id, None)
    return END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text("Операция отменена.")
    user_data.pop(user_id, None)
    current_step.pop(user_id, None)
    return END
