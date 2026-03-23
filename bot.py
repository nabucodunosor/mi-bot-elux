async def responder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    resultados = buscar_productos(user_text)
    
    # Simplificamos los resultados para que la IA no se trabe con símbolos raros
    lista_precios = ""
    for p in resultados:
        lista_precios += f"- {p['descripcion']}: ${p['precio']}\n"

    # Instrucción ultra-clara
    instruccion = f"""
    Eres el asistente de Elux. 
    Datos del local: Calle 20 N° 498 casi 42, La Plata. Lunes a Viernes 9-18hs, Sábados 9-13hs.
    Stock encontrado para esta duda:
    {lista_precios}
    
    Responde al cliente de forma breve en español de Argentina: {user_text}
    """

    try:
        # Forzamos una configuración más relajada de seguridad
        response = model.generate_content(instruccion)
        if response.text:
            await update.message.reply_text(response.text)
        else:
            raise Exception("Respuesta vacía")
    except Exception as e:
        print(f"⚠️ Error en Gemini: {e}")
        # Si la IA falla, mandamos la info de horarios o productos a mano
        if "horario" in user_text.lower():
            await update.message.reply_text("Atendemos de Lunes a Viernes de 9 a 18hs y Sábados de 9 a 13hs en Calle 20 N° 498.")
        elif resultados:
            await update.message.reply_text(f"Mirá, no pude procesar el mensaje con la IA, pero acá tenés los precios:\n{lista_precios}")
        else:
            await update.message.reply_text("Che, estoy con una falla en la conexión. Escribinos al WhatsApp 221 399 3484 y te pasamos el precio al toque.")
