
import os
import logging
import subprocess
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)

TOKEN = '8318048756:AAEp0hAgvDNLLbgbpUuqlQQaWv9EL5sBRIU'

logging.basicConfig(level=logging.INFO)

user_pitch = {}

PITCH_MAP = {
    "pitch_-3.0": 0.841,
    "pitch_-3.1": 0.825,
    "pitch_-2.9": 0.857,
    "pitch_-2.8": 0.873
}

def get_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎚 –2.8", callback_data="pitch_-2.8"),
            InlineKeyboardButton("🎚 –2.9", callback_data="pitch_-2.9"),
        ],
        [
            InlineKeyboardButton("🎚 –3.0", callback_data="pitch_-3.0"),
            InlineKeyboardButton("🎚 –3.1", callback_data="pitch_-3.1"),
        ]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Пришли видео, кружок или голосовое — я понижу голос и пришлю обратно.\n"
        "🎛 Выбери питч:", reply_markup=get_keyboard()
    )

async def pitch_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    pitch_key = query.data
    user_pitch[query.from_user.id] = PITCH_MAP[pitch_key]
    await query.edit_message_text(text=f"✅ Установлен питч {pitch_key.replace('pitch_', '-')}")

async def process_audio(input_path: str, output_path: str, pitch_factor: float, is_voice=False):
    atempo = 1.0 / pitch_factor
    cmd = [
        'ffmpeg', '-i', input_path,
        '-filter:a', f'asetrate=44100*{pitch_factor},atempo={atempo}',
        '-c:a', 'libopus' if is_voice else 'aac',
        '-vn', output_path, '-y'
    ]
    subprocess.run(cmd, shell=False)

async def process_video(input_path: str, output_path: str, pitch_factor: float):
    audio_path = "audio_temp.aac"
    pitched_audio_path = "pitched_audio.aac"

    subprocess.run(['ffmpeg', '-i', input_path, '-q:a', '0', '-map', 'a', audio_path, '-y'], shell=False)
    await process_audio(audio_path, pitched_audio_path, pitch_factor)
    subprocess.run(['ffmpeg', '-i', input_path, '-i', pitched_audio_path, '-c:v', 'copy',
                    '-map', '0:v:0', '-map', '1:a:0', output_path, '-y'], shell=False)

    os.remove(audio_path)
    os.remove(pitched_audio_path)

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pitch = user_pitch.get(update.effective_user.id, 0.825)
    file = await update.message.video.get_file()
    input_path = "input.mp4"
    output_path = "output.mp4"

    await file.download_to_drive(input_path)
    await process_video(input_path, output_path, pitch)
    await update.message.reply_video(video=open(output_path, "rb"))
    os.remove(input_path)
    os.remove(output_path)

async def handle_video_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pitch = user_pitch.get(update.effective_user.id, 0.825)
    file = await update.message.video_note.get_file()
    input_path = "input_note.mp4"
    output_path = "output_note.mp4"

    await file.download_to_drive(input_path)
    await process_video(input_path, output_path, pitch)
    await update.message.reply_video_note(video_note=open(output_path, "rb"))
    os.remove(input_path)
    os.remove(output_path)

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pitch = user_pitch.get(update.effective_user.id, 0.825)
    file = await update.message.voice.get_file()
    input_path = "input_voice.ogg"
    output_path = "output_voice.ogg"

    await file.download_to_drive(input_path)
    await process_audio(input_path, output_path, pitch, is_voice=True)
    await update.message.reply_voice(voice=open(output_path, "rb"))
    os.remove(input_path)
    os.remove(output_path)

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(pitch_button))
    app.add_handler(MessageHandler(filters.VIDEO, handle_video))
    app.add_handler(MessageHandler(filters.VIDEO_NOTE, handle_video_note))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.run_polling()

if __name__ == "__main__":
    main()
