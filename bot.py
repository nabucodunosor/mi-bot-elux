import os
import json
import re
from groq import Groq
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes

# ── Cargar catálogo ──────────────────────────────────────────
with open("productos.json", "r", encoding="utf-8") as f:
    PRODUCTOS = json.load(f)

print(f"✅ Catálogo cargado: {len(PRODUCTOS)} productos")

# ── Config ───────────────────────────────────────────────────
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
GROQ_API_KEY   = os.environ.get("GROQ_API_KEY", "")
client = Groq(api_key=GROQ_API_KEY)

SYSTEM_PROMPT = """Sos el asistente virtual de Elux Materiales Eléctricos, un local de venta de materiales eléctricos en La Plata, Argentina. Atendés consultas de clientes por Telegram.

=== DATOS DEL NEGOCIO ===
- Dirección: Calle 20 N° 498 casi 42, La Plata, Buenos Aires
- WhatsApp: 221 399 3484
- Marcas principales: Conductores Kalop, Interruptores Jeluz, Térmicas y disyuntores SICA y ABB
- Formas de pago: efectivo y transferencia bancaria (NO se aceptan tarjetas)
- Envíos: NO se realizan, solo venta en el local
- Horarios: Lunes a viernes 9 a 18hs, sábados 9 a 13hs

=== CÓMO RESPONDER CONSULTAS DE PRODUCTOS ===
Cuando el sistema te provea resultados de búsqueda, SIEMPRE:
1. Confirmá que tenemos el producto
2. Listá los productos encontrados con su código y precio
3. Aclará que el precio es orientativo y puede variar
4. Indicá que el stock debe confirmarse
5. Invitá a contactar por WhatsApp para descuentos o más info

Ejemplo de buena respuesta:
"¡Sí, tenemos apliques LED negros! Acá te paso algunas opciones:

• [94874-N] LAVY1 - Aplique 1 luz GU10 Negro → $12.904
• [94875-N] LAVY2 - Aplique 2 luces GU10 Negro → $25.948
• [95240] AKIRA II - Aplique LED 10W Negro → $69.808

Los precios son orientativos y pueden variar. Para confirmar stock y consultar descuentos escribinos al WhatsApp 221 399 3484 😊"

=== CUANDO NO HAY RESULTADOS ===
Si la búsqueda no devuelve productos, sugerí términos alternativos y derivá al WhatsApp.

=== REGLAS GENERALES ===
- Respondé siempre en español rioplatense
- Sé amigable y cercano
- Usá emojis con moderación
- Texto plano, sin markdown con asteriscos ni guiones bajos
- Máximo 200 palabras por respuesta"""

# ── Búsqueda en catálogo ─────────────────────────────────────
def buscar_productos(query: str, limite: int = 8):
    if not query or len(query) < 2:
        return [], 0

    # Por código exacto
    por_codigo = [p for p in PRODUCTOS if p["codigo"].lower() == query.lower()]

    # Por palabras clave
    stopwords = {"el","la","los","las","un","una","de","del","que","en","es","con",
                 "por","para","me","te","se","le","y","o","a","al","hay","tiene",
                 "tienen","precio","cuanto","cuánto","busco","necesito","stock",
                 "quiero","quisiera","tenés","tienen","tienen","dame","mostrame"}
    terms = [t for t in query.lower().split() if len(t) > 2 and t not in stopwords]

    por_desc = []
    if terms:
        for p in PRODUCTOS:
            if p in por_codigo:
                continue
            haystack = (p["codigo"] + " " + p["descripcion"]).lower()
            if all(t in haystack for t in terms):
                por_desc.append(p)

    todos = por_codigo + por_desc
    return todos[:limite], len(todos)

def detectar_busqueda(texto: str) -> bool:
    keywords = ["precio","cuanto","cuánto","tienen","busco","buscar","necesito",
                "hay","stock","costo","vale","producto","modelo","código","codigo",
                "quiero","quisiera","mostrame","tenés","cable","aplique","térmica",
                "termica","disyuntor","interruptor","conductor","tablero","caño",
                "led","luminaria","lampara","lámpara","foco","tomacorriente","llave"]
    lower = texto.lower()
    if any(k in lower for k in keywords):
        return True
    if re.match(r"^\d{4,}", texto.strip()):
        return True
    stopwords = {"el","la","los","las","un","una","de","del","que","en","es",
                 "con","por","para","me","te","se","le","y","o","a","al"}
    words = [w for w in lower.split() if len(w) > 2 and w not in stopwords]
    return len(words) >= 2

def formato_precio(precio: float) -> str:
    return f"${precio:,.0f}".replace(",", ".")

def construir_contexto_productos(texto: str) -> str:
    resultados, total = buscar_productos(texto)

    if not resultados:
        return "\n\n[BÚSQUEDA EN CATÁLOGO: No se encontraron productos que coincidan con esta consulta. Sugerí al cliente que intente con otros términos o que contacte al WhatsApp.]"

    ctx = f"\n\n[RESULTADOS DEL CATÁLOGO - {total} productos encontrados, mostrando {len(resultados)}]\n"
    for p in resultados:
        ctx += f"Código: {p['codigo']} | {p['descripcion']} | Precio: {formato_precio(p['precio_venta'])}\n"
    ctx += "[FIN DE RESULTADOS - Presentá estos productos al cliente de forma clara y amigable]"
    return ctx

# ── Historial de conversación por usuario ────────────────────
conversaciones = {}

def get_historial(user_id: int) -> list:
    if user_id not in conversaciones:
        conversaciones[user_id] = []
    return conversaciones[user_id]

def agregar_mensaje(user_id: int, role: str, content: str):
    historial = get_historial(user_id)
    historial.append({"role": role, "content": content})
    # Mantener solo los últimos 10 mensajes para no exceder el contexto
    if len(historial) > 10:
        conversaciones[user_id] = historial[-10:]

# ── Handlers ─────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conversaciones[user_id] = []  # Limpiar historial al iniciar
    await update.message.reply_text(
        "⚡ Hola! Soy el asistente de Elux Materiales Eléctricos.\n\n"
        "Podés preguntarme por productos, precios, horarios o cualquier consulta.\n\n"
        "📍 Calle 20 N° 498 casi 42, La Plata\n"
        "📱 WhatsApp: 221 399 3484\n\n"
        "En qué te puedo ayudar?"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.strip()
    user_id = update.effective_user.id
    if not texto:
        return

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing"
    )

    # Buscar productos si corresponde
    product_context = ""
    if detectar_busqueda(texto):
        product_context = construir_contexto_productos(texto)

    # Agregar mensaje del usuario al historial
    agregar_mensaje(user_id, "user", texto + product_context)

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                *get_historial(user_id)
            ],
            max_tokens=600,
            temperature=0.7
        )
        reply = response.choices[0].message.content

        # Guardar respuesta en historial
        agregar_mensaje(user_id, "assistant", reply)

    except Exception as e:
        reply = "Hubo un error al procesar tu consulta. Escribinos al WhatsApp 221 399 3484."
        print(f"Error Groq: {e}")

    await update.message.reply_text(reply)

# ── Main ─────────────────────────────────────────────────────
def main():
    if not TELEGRAM_TOKEN:
        raise ValueError("Falta TELEGRAM_TOKEN")
    if not GROQ_API_KEY:
        raise ValueError("Falta GROQ_API_KEY")

    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🤖 Bot Elux iniciado con Groq llama-3.3-70b...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
