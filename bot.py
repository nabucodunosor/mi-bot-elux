import os
import json
import google.generativeai as genai
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# --- 1. CARGAR CATÁLOGO ---
try:
    with open("productos.json", "r", encoding="utf-8") as f:
        PRODUCTOS = json.load(f)
    print(f"✅ Catálogo cargado: {len(PRODUCTOS)} productos.")
except Exception as e:
    print(f"❌ Error productos.json: {e}")
    PRODUCTOS = []

# --- 2. CONFIGURACIÓN IA ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")

# Intentamos configurar la IA con el modelo más compatible
try:
    genai.configure(api_key=GOOGLE_API_KEY)
    # Cambiamos a 'gemini-1.5-flash' a secas, que es el estándar
    model = genai.GenerativeModel('gemini-1.5-flash') 
except:
    model = None

SYSTEM_PROMPT = "Sos el experto de Elux (La Plata). Hablá en rioplatense, sé breve y vendedora."

# --- 3. LÓGICA DE BÚSQUEDA ---
def buscar_productos(texto):
    texto = texto.lower()
    return [p for p in PRODUCTOS if texto in p['descripcion'].lower()][:5]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("¡Buenas! Soy el asistente de Elux. ¿Qué materiales buscás hoy?")

async def responder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    resultados = buscar_productos(user_text)
    
    # 1. Preparamos la info de precios
    info_precios = ""
    if resultados:
        info_precios = "Mirá, acá encontré estos precios en el sistema:\n"
        for p in resultados:
            info_precios += f"• {p['descripcion']}: ${p['precio']}\n"
    
    # 2. Intentamos que la IA procese la respuesta con onda
    try:
        prompt = f"{SYSTEM_PROMPT}\nStock: {info_precios}\nCliente dice: {user_text}"
        response = model.generate_content(prompt)
        await update.message.reply_text(response.text)
    
    except Exception as e:
        print(f"⚠️ Error Gemini: {e}")
        # 3. SI LA IA FALLA, MANDAMOS LOS PRECIOS PELADOS (Para que no sea un tarado)
        if resultados:
            msg_emergencia = f"Che, la IA está medio lenta, pero acá tenés los precios:\n\n{info_precios}\n¿Te sirve algo? Avisame o mandame al WhatsApp 221 399 3484."
            await update.message.reply_text(msg_emergencia)
        else:
            # Si no hay productos y falla la IA, damos los horarios/contacto
            if "horario" in user_text.lower() or "donde" in user_text.lower():
                 await update.message.reply_text("Estamos en Calle 20 N° 498. Lun-Vie 9-18hs y Sáb 9-13hs.")
            else:
                 await update.message.reply_text("Perdón, tuve un error de conexión. Consultame al WhatsApp 221 399 3484 y te paso el precio al toque.")

# --- 4. ARRANQUE ---
if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder))
    print("🚀 Bot de QUID / Elux en marcha...")
    app.run_polling()
