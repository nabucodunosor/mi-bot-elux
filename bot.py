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

# ── Config Groq ──────────────────────────────────────────────
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
GROQ_API_KEY   = os.environ.get("GROQ_API_KEY", "")
client = Groq(api_key=GROQ_API_KEY)

SYSTEM_PROMPT = """Sos el asistente virtual de Elux Materiales Eléctricos, un local de venta de materiales eléctricos en La Plata, Argentina.

Información del negocio:
- Dirección: Calle 20 N° 498 casi 42, La Plata, Buenos Aires
- WhatsApp: 221 399 3484
- Marcas: Conductores Kalop, Interruptores Jeluz, Térmicas y disyuntores SICA y ABB
- Pago: efectivo y transferencia bancaria (no tarjetas)
- Envíos: no se realizan, solo venta en el local
- Horarios: Lunes a viernes 9-18hs, sábados 9-13hs

Reglas:
- Respondé en español rioplatense, de forma amigable y breve (máximo 4 oraciones)
- Los precios que te muestran YA tienen el margen aplicado — son los precios finales para el cliente
- SIEMPRE aclarás que los precios son orientativos, que hay que consultar por descuentos y confirmar stock
- Para confirmar stock o pedir descuentos, siempre derivá al WhatsApp: 221 399 3484
- No inventes productos ni precios que no estén en los resultados de búsqueda
- Usá formato simple de texto, sin markdown"""

# ── Búsqueda en catálogo ─────────────────────────────────────
def buscar_productos(query: str, limite: int = 6):
    if not query or len(query) < 2:
        return [], 0
    por_codigo = [p for p in PRODUCTOS if p["codigo"].lower() == query.lower()]
    stopwords = {"el","la","los","las","un","una","de","del","que","en","es","con",
                 "por","para","me","te","se","le","y","o","a","al","hay","tiene",
                 "tienen","precio","cuanto","cuánto","busco","necesito","stock"}
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
                "hay","stock","costo","vale","producto","modelo","código","codigo"]
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
        return "\n\nBÚSQUEDA EN CATÁLOGO: No se encontraron productos que coincidan."
    ctx = f"\n\nRESULTADOS DE BÚSQUEDA ({total} encontrados, mostrando {len(resultados)}):\n"
    for p in resultados:
        ctx += f"- [{p['codigo']}] {p['descripcion']} → {formato_precio(p['precio_venta'])}\n"
    return ctx

# ── Handlers ─────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⚡ Hola! Soy el asistente de Elux Materiales Eléctricos.\n\n"
        "Podés preguntarme por productos, precios, horarios o cualquier consulta.\n\n"
        "📍 Calle 20 N° 498 casi 42, La Plata\n"
        "📱 WhatsApp: 221 399 3484"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.strip()
    if not texto:
        return

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing"
    )

    product_context = ""
    if detectar_busqueda(texto):
        product_context = construir_contexto_productos(texto)

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": texto + product_context}
            ],
            max_tokens=500
        )
        reply = response.choices[0].message.content
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

    print("🤖 Bot Elux iniciado con Groq...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
