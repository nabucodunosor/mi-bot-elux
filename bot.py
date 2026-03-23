import os
import json
import google.generativeai as genai
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- CARGAR CATÁLOGO ---
try:
    with open("productos.json", "r", encoding="utf-8") as f:
        PRODUCTOS = json.load(f)
    print(f"✅ Catálogo cargado: {len(PRODUCTOS)} productos.")
except Exception as e:
    print(f"❌ Error al cargar productos.json: {e}")
    PRODUCTOS = []

# --- CONFIGURACIÓN ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")

genai.configure(api_key=GOOGLE_API_KEY)
# Usamos 1.5-flash que es más estable para mensajes rápidos
model = genai.GenerativeModel('gemini-1.5-flash')

SYSTEM_PROMPT = """Sos el asistente de Elux Materiales Eléctricos (La Plata). 
Respondé SIEMPRE en español rioplatense, amigable y muy breve.
Si te paso productos del catálogo, decile el precio al cliente. 
Los precios YA tienen el margen, son finales."""

# --- FUNCIONES ---
def buscar_productos(texto):
    texto = texto.lower()
    # Buscamos coincidencias en la descripción
    encontrados = [p for p in PRODUCTOS if texto in p['descripcion'].lower()]
    # Devolvemos solo los primeros 5 para no saturar a la IA
    return encontrados[:5]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("¡Hola! Soy el bot de Elux. ¿Qué materiales estás buscando hoy?")

async def responder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    resultados = buscar_productos(user_text)
    
    # Armamos el mensaje para la IA
    contexto_productos = f"\nProductos encontrados en stock: {resultados}" if resultados else "\nNo se encontraron productos exactos."
    instruccion = f"{SYSTEM_PROMPT}\n\nCliente pregunta: {user_text}\n{contexto_productos}"

    try:
        # Generar respuesta con Gemini
        response = model.generate_content(instruccion)
        await update.message.reply_text(response.text)
    except Exception as e:
        print(f"⚠️ Error en Gemini: {e}")
        # Si falla la IA, al menos intentamos darle los precios directo
        if resultados:
            respuesta_emergencia = "Che, tengo un problema con la IA, pero acá encontré esto:\n"
            for p in resultados:
                respuesta_emergencia += f"- {p['descripcion']}: ${p['precio']}\n"
            await update.message.reply_text(respuesta_emergencia)
        else:
            await update.message.reply_text("Perdón, me tiró un error la conexión. ¿Me repetís o me hablás al WhatsApp?")

# --- ARRANQUE ---
if __name__ == '__main__':
    if not TELEGRAM_TOKEN or not GOOGLE_API_KEY:
        print("❌ FALTAN VARIABLES DE ENTORNO. Revisá Railway.")
    else:
        app = Application.builder().token(TELEGRAM_TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder))
        print("🚀 Bot funcionando...")
        app.run_polling()
