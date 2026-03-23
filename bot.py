import os
import json
import google.generativeai as genai
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# --- 1. CARGAR CATÁLOGO ---
try:
    with open("productos.json", "r", encoding="utf-8") as f:
        PRODUCTOS = json.load(f)
    print(f"✅ Catálogo cargado con {len(PRODUCTOS)} productos.")
except Exception as e:
    print(f"❌ Error al cargar productos.json: {e}")
    PRODUCTOS = []

# --- 2. CONFIGURACIÓN DE LLAVES ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")

# Configurar IA
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# Instrucciones para el bot
SYSTEM_PROMPT = """Sos el asistente de Elux Materiales Eléctricos en La Plata. 
Respondé SIEMPRE en español rioplatense, amable y muy breve.
Si el usuario pregunta por productos, usá la lista que te paso. 
Los precios ya incluyen el margen, son finales.
Si no encontrás algo, decile que nos consulte al WhatsApp 221 399 3484."""

# --- 3. FUNCIONES DE LÓGICA ---
def buscar_en_catalogo(consulta):
    consulta = consulta.lower()
    # Busca coincidencias en la descripción del producto
    encontrados = [p for p in PRODUCTOS if consulta in p['descripcion'].lower()]
    # Devolvemos solo los 5 mejores para que la IA no se maree
    return encontrados[:5]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("¡Hola! Soy el asistente de Elux. ¿Qué materiales estás buscando?")

async def responder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    
    # Manejo rápido de horarios para no gastar IA
    if any(palabra in user_text.lower() for palabra in ["horario", "abierto", "donde estan", "direccion"]):
        await update.message.reply_text("Estamos en Calle 20 N° 498 (casi 42), La Plata. 🕙 Lunes a Viernes 9-18hs y Sábados 9-13hs.")
        return

    # Búsqueda de productos
    resultados = buscar_en_catalogo(user_text)
    
    # Armamos el texto para la IA
    contexto = f"\nProductos en stock: {resultados}" if resultados else "\nNo hay coincidencias exactas en el catálogo."
    prompt_final = f"{SYSTEM_PROMPT}\n\nConsulta del cliente: {user_text}\n{contexto}"

    try:
        response = model.generate_content(prompt_final)
        if response.text:
            await update.message.reply_text(response.text)
        else:
            raise Exception("Respuesta vacía")
    except Exception as e:
        print(f"⚠️ Error en Gemini: {e}")
        # Si falla la IA, mostramos los resultados directo (Plan B)
        if resultados:
            texto_b = "Che, tengo una falla en la conexión, pero acá encontré esto:\n"
            for p in resultados:
                texto_b += f"• {p['descripcion']}: ${p['precio']}\n"
            await update.message.reply_text(texto_b)
        else:
            await update.message.reply_text("Perdón, me tiró un error la conexión. ¿Me repetís o me hablás al WhatsApp 221 399 3484?")

# --- 4. ARRANQUE DEL BOT ---
if __name__ == '__main__':
    if not TELEGRAM_TOKEN or not GOOGLE_API_KEY:
        print("❌ ERROR: Faltan las variables TELEGRAM_TOKEN o GOOGLE_API_KEY en Railway.")
    else:
        # Usamos ApplicationBuilder para evitar el error de 'Updater'
        application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
        
        application.add_handler(CommandHandler("start", start))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder))
        
        print("🚀 Bot Elux encendido y escuchando...")
        application.run_polling()
