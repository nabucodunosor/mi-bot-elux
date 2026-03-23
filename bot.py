import os
import json
import re
import google.generativeai as genai
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes

# ── CONFIGURACIÓN ──────────────────────────────────────────
with open("productos.json", "r", encoding="utf-8") as f:
    PRODUCTOS = json.load(f)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")

genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

SYSTEM_PROMPT = """IMPORTANTE: Respondé SIEMPRE en español rioplatense (de Argentina). No uses otros idiomas bajo ninguna circunstancia.

Sos el asistente virtual de Elux Materiales Eléctricos, un local de venta de materiales eléctricos en La Plata, Argentina.

Información del negocio:
- Dirección: Calle 20 N° 498 casi 42, La Plata, Buenos Aires
- WhatsApp: 221 399 3484
- Pago: efectivo y transferencia bancaria (no tarjetas)
- Horarios: Lunes a viernes 9-18hs, sábados 9-13hs

Reglas:
- Respondé en español rioplatense, de forma amigable y breve.
- Los precios del catálogo YA tienen el margen aplicado.
"""

# ── FUNCIONES ──────────────────────────────────────────────
def buscar_productos(termino):
    termino = termino.lower()
    resultados = [p for p in PRODUCTOS if termino in p['descripcion'].lower()]
    return resultados[:5]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("¡Hola! Soy el asistente de Elux. ¿En qué te puedo ayudar?")

async def manejar_mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto_usuario = update.message.text
    
    # Buscar productos en el JSON
    matches = buscar_productos(texto_usuario)
    contexto_productos = ""
    if matches:
        contexto_productos = "\nProductos encontrados: " + str(matches)

    try:
        chat = model.start_chat(history=[])
        response = chat.send_message(f"{SYSTEM_PROMPT}\n\nUsuario dice: {texto_usuario}\n{contexto_productos}")
        await update.message.reply_text(response.text)
    except Exception as e:
        print(f"Error: {e}")
        await update.message.reply_text("Hubo un error. Intentá de nuevo o contactanos al WhatsApp.")

# ── MAIN ───────────────────────────────────────────────────
if __name__ == "__main__":
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, manejar_mensaje))
    print("✅ Bot iniciado")
    app.run_polling()
