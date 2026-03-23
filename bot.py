import os
import json
import google.generativeai as genai
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Cargar catálogo
with open("productos.json", "r", encoding="utf-8") as f:
    PRODUCTOS = json.load(f)

# Configuración
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")

genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

SYSTEM_PROMPT = "Respondé siempre en español rioplatense. Sos el asistente de Elux Materiales Eléctricos. Sé breve."

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("¡Hola! Soy el bot de Elux. ¿Qué necesitás?")

async def responder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    busqueda = [p for p in PRODUCTOS if user_text.lower() in p['descripcion'].lower()][:3]
    prompt = f"{SYSTEM_PROMPT}\nInfo: {busqueda}\nUsuario: {user_text}"
    
    try:
        response = model.generate_content(prompt)
        await update.message.reply_text(response.text)
    except Exception as e:
        print(f"Error: {e}")
        await update.message.reply_text("Perdón, tuve un error. ¿Podés repetir?")

if __name__ == '__main__':
    # Creamos la aplicación de la forma más compatible posible
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder))
    
    print("Bot encendido y escuchando...")
    application.run_polling()
