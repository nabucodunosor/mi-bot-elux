import os
import json
import google.generativeai as genai
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# --- CARGAR CATÁLOGO ---
try:
    with open("productos.json", "r", encoding="utf-8") as f:
        PRODUCTOS = json.load(f)
    print(f"✅ Catálogo cargado: {len(PRODUCTOS)} productos.")
except Exception as e:
    print(f"❌ Error productos.json: {e}")
    PRODUCTOS = []

# --- CONFIGURACIÓN ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")

if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')

SYSTEM_PROMPT = "Sos el asistente de Elux Materiales Eléctricos (La Plata). Respondé siempre en español rioplatense, amigable y muy breve."

# --- FUNCIONES ---
def buscar_productos(texto):
    texto = texto.lower()
    return [p for p in PRODUCTOS if texto in p['descripcion'].lower()][:5]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("¡Hola! Soy el bot de Elux. ¿Qué materiales buscás?")

async def responder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    resultados = buscar_productos(user_text)
    
    lista_precios = ""
    for p in resultados:
        lista_precios += f"- {p['descripcion']}: ${p['precio']}\n"

    # Si pregunta por horarios específicamente
    if "horario" in user_text.lower() or "abierto" in user_text.lower():
        await update.message.reply_text("Estamos de Lunes a Viernes de 9 a 18hs y Sábados de 9 a 13hs en Calle 20 N° 498.")
        return

    prompt = f"{SYSTEM_PROMPT}\nStock: {lista_precios}\nUsuario: {user_text}"

    try:
        response = model.generate_content(prompt)
        await update.message.reply_text(response.text)
    except Exception as e:
        print(f"⚠️ Error: {e}")
        if resultados:
            await update.message.reply_text(f"No pude procesar con la IA, pero acá tenés precios:\n{lista_precios}")
        else:
            await update.message.reply_text("Perdón, tuve un error de conexión. ¿Me repetís?")

# --- ARRANQUE ---
if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder))
    print("🚀 Bot en marcha...")
    app.run_polling()
