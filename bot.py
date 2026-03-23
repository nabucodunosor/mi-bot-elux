import os
import json
import google.generativeai as genai
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes

# Cargar catálogo
with open("productos.json", "r", encoding="utf-8") as f:
    PRODUCTOS = json.load(f)

# Configuración de llaves
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")

genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

SYSTEM_PROMPT = """IMPORTANTE: Respondé SIEMPRE en español rioplatense.
Sos el asistente de Elux Materiales Eléctricos en La Plata.
Reglas: Sé breve, amable y usá los precios del catálogo que ya tienen el margen aplicado."""

def buscar_productos(termino):
    termino = termino.lower()
    return [p for p in PRODUCTOS if termino in p['descripcion'].lower()][:5]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("¡Hola! Soy el asistente de Elux. ¿Qué material buscás?")

async def manejar_mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text
    busqueda = buscar_productos(texto)
    contexto = f"\nProductos: {busqueda}" if busqueda else ""
    
    try:
        response = model.generate_content(f"{SYSTEM_PROMPT}\nUsuario: {texto}\n{contexto}")
        await update.message.reply_text(response.text)
    except:
        await update.message.reply_text("Error de conexión. Intentá de nuevo.")

if __name__ == "__main__":
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, manejar_mensaje))
    app.run_polling()
