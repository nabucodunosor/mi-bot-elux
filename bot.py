import os
import json
import google.generativeai as genai
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# 1. CARGAR PRODUCTOS
try:
    with open("productos.json", "r", encoding="utf-8") as f:
        PRODUCTOS = json.load(f)
except:
    PRODUCTOS = []

# 2. CONFIGURACIÓN (Directa)
genai.configure(api_key=os.environ.get("GOOGLE_API_KEY", ""))
model = genai.GenerativeModel('gemini-1.5-flash')

async def responder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    # BUSQUEDA MANUAL (No depende de la IA para encontrar el precio)
    resultados = [p for p in PRODUCTOS if user_text.lower() in p['descripcion'].lower()][:3]
    
    precios_texto = ""
    for p in resultados:
        precios_texto += f"• {p['descripcion']}: ${p['precio']}\n"

    try:
        # Intentamos que la IA solo le dé "forma" al mensaje
        prompt = f"Sos el bot de Elux. El cliente dice: '{user_text}'. Info de precios: {precios_texto}. Respondé cortito."
        response = model.generate_content(prompt)
        await update.message.reply_text(response.text)
    except:
        # SI LA IA FALLA, EL BOT RESPONDE ESTO SÍ O SÍ (Sin IA)
        if precios_texto:
            await update.message.reply_text(f"Acá tenés los precios:\n{precios_texto}")
        else:
            await update.message.reply_text("No encontré eso. Consultanos al 221 399 3484.")

if __name__ == '__main__':
    app = ApplicationBuilder().token(os.environ.get("TELEGRAM_TOKEN", "")).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder))
    app.run_polling()
