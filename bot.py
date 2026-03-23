import os
import json
import google.generativeai as genai
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# --- 1. CARGAR CATÁLOGO (QUID / ELUX) ---
try:
    with open("productos.json", "r", encoding="utf-8") as f:
        PRODUCTOS = json.load(f)
    print(f"✅ Catálogo cargado: {len(PRODUCTOS)} productos.")
except Exception as e:
    print(f"❌ Error productos.json: {e}")
    PRODUCTOS = []

# --- 2. CONFIGURACIÓN IA (EL CEREBRO) ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")

genai.configure(api_key=GOOGLE_API_KEY)
# Cambiamos a la versión específica que no tira 404
model = genai.GenerativeModel('gemini-1.5-flash-latest') 

SYSTEM_PROMPT = """Sos el experto en ventas de Elux Materiales Eléctricos (La Plata). 
Tu misión es ASESORAR y VENDER. 
- Hablá en español rioplatense (che, mirá, tenés).
- Si el cliente busca algo, usá los precios que te paso.
- Si no está lo exacto, ofrecele lo más parecido (ej: si busca cable de 1.5 y no hay, ofrecele de 2.5 explicando por qué es mejor).
- Si te preguntan por horarios o ubicación: Calle 20 N° 498, Lun-Vie 9-18hs, Sáb 9-13hs.
"""

# --- 3. LÓGICA DE BÚSQUEDA ---
def buscar_productos(texto):
    texto = texto.lower()
    return [p for p in PRODUCTOS if texto in p['descripcion'].lower()][:6]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("¡Buenas! Soy el asistente de Elux. ¿Qué materiales necesitás para tu obra?")

async def responder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    resultados = buscar_productos(user_text)
    
    # Formateamos los precios para que la IA los entienda fácil
    lista_precios = ""
    if resultados:
        for p in resultados:
            lista_precios += f"- {p['descripcion']}: ${p['precio']}\n"
    else:
        lista_precios = "No encontré el producto exacto en el catálogo."

    # Armamos el pedido a la IA
    prompt_final = f"{SYSTEM_PROMPT}\n\nCatálogo disponible:\n{lista_precios}\n\nCliente dice: {user_text}"

    try:
        response = model.generate_content(prompt_final)
        if response.text:
            await update.message.reply_text(response.text)
        else:
            raise Exception("Respuesta vacía de Gemini")
            
    except Exception as e:
        print(f"⚠️ Error en Gemini: {e}")
        # PLAN B: Si la IA falla, que no sea un tarado y dé la info rústica
        if resultados:
            msg = "Mirá, ando con un problema técnico, pero acá te encontré estos precios en el sistema:\n\n"
            msg += lista_precios
            msg += "\n¿Te sirve alguno? Si no, hablame al WhatsApp 221 399 3484."
            await update.message.reply_text(msg)
        else:
            await update.message.reply_text("Perdón che, me anda mal la conexión. Consultame al WhatsApp 221 399 3484 que te paso el precio al toque.")

# --- 4. ARRANQUE ---
if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder))
    print("🚀 Obrero de QUID Soluciones en marcha...")
    app.run_polling()
