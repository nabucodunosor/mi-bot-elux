import os
import json
import google.generativeai as genai
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes

# --- CONFIGURACIÓN ---
with open("productos.json", "r", encoding="utf-8") as f:
    PRODUCTOS = json.load(f)

# Variables desde Railway
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")

genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

SYSTEM_PROMPT = """Respondé siempre en español rioplatense. 
Sos el asistente de Elux Materiales Eléctricos. 
Si el usuario pregunta por productos, usá la info que te paso. 
Sé breve y amable."""

# --- LÓGICA ---
def buscar_en_catalogo(query):
    query = query.lower()
    encontrados = [p for p in PRODUCTOS if query in p['descripcion'].lower()]
    return encontrados[:5]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("¡Hola! Soy el bot de Elux. ¿En qué te puedo ayudar?")

async def responder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    items = buscar_en_catalogo(user_text)
    
    prompt_final = f"{SYSTEM_PROMPT}\nCatalogo actual: {items}\nUsuario: {user_text}"
    
    try:
        response = model.generate_content(prompt_final)
        await update.message.reply_text(response.text)
    except Exception as e:
        print(f"Error Gemini: {e}")
        await update.message.reply_text("Perdón, tuve un problema. ¿Podés repetir?")

# --- ARRANQUE ---
if __name__ == '__main__':
    # Usamos ApplicationBuilder que es lo más estable hoy
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), responder))
    
    print("Bot encendido...")
    app.run_polling()
