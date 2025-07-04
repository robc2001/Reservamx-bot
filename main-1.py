# main.py
from flask import Flask, request
import asyncio
import telegram
import logging

from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes,
    MessageHandler, ConversationHandler, filters
)
import gspread
from oauth2client.service_account import ServiceAccountCredentials

TELEGRAM_TOKEN = "7738129492:AAEVZQbzjd3jx4oGI4btgvWZBe7YQFYJm_o"
ADMIN_ID = "5920985997"

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)
sheet = client.open("Reservaciones RESERVAMX").sheet1

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

TIPO, LUGAR, NOMBRE, FECHA, PERSONAS = range(5)
tipos = [["Rooftop", "Restaurante", "Antro"]]
rooftops = ["Pandora", "Sono", "Fiera", "Faunna", "Supra", "Sana Sana"]
restaurantes = ["Mexa Cocina del Alma", "Barbaro", "Bagatelle"]
antros = ["Panem", "Alma", "Phonique", "Phonique Puebla", "Duke", "Duke San Miguel A.",
          "Montana", "Montana Bay", "Symphonie", "Alvar", "Bocca", "Despecho Disco Palmas",
          "Antro Juan", "Romeo", "Secret Sunday"]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    markup = ReplyKeyboardMarkup(tipos, one_time_keyboard=True)
    await update.message.reply_text(" Bienvenido a *RESERVAMX*.\nQue deseas reservar?", parse_mode="Markdown", reply_markup=markup)
    return TIPO

async def elegir_tipo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["tipo"] = update.message.text
    opciones = rooftops if update.message.text=="Rooftop" else restaurantes if update.message.text=="Restaurante" else antros
    markup = ReplyKeyboardMarkup([[op] for op in opciones], one_time_keyboard=True)
    await update.message.reply_text(f"Cual {update.message.text.lower()} quieres reservar?", reply_markup=markup)
    return LUGAR

async def elegir_lugar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["lugar"] = update.message.text
    await update.message.reply_text("A nombre de quien?", reply_markup=ReplyKeyboardRemove())
    return NOMBRE

async def obtener_nombre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["nombre"] = update.message.text
    await update.message.reply_text("Fecha y hora de la reservacion?")
    return FECHA

async def obtener_fecha(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["fecha"] = update.message.text
    await update.message.reply_text("Numero de personas?")
    return PERSONAS

async def obtener_personas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    datos = context.user_data
    sheet.append_row([datos["tipo"], datos["lugar"], datos["nombre"], datos["fecha"], datos["personas"]])
    await update.message.reply_text(
        f" Reservacion para *{datos['personas']} personas* en *{datos['lugar']}* el *{datos['fecha']}* confirmada!\n\n"
        " *Gracias por reservar con RESERVAMX*",
        parse_mode="Markdown"
    )
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f" Nueva reservacion:\nTipo: {datos['tipo']}\nLugar: {datos['lugar']}\nNombre: {datos['nombre']}\nFecha: {datos['fecha']}\nPersonas: {datos['personas']}"
    )
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Reservacion cancelada.")
    return ConversationHandler.END

app_flask = Flask(__name__)
application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

# Reutilizamos tus handlers
conv = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        TIPO: [MessageHandler(filters.TEXT & ~filters.COMMAND, elegir_tipo)],
        LUGAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, elegir_lugar)],
        NOMBRE: [MessageHandler(filters.TEXT & ~filters.COMMAND, obtener_nombre)],
        FECHA: [MessageHandler(filters.TEXT & ~filters.COMMAND, obtener_fecha)],
        PERSONAS: [MessageHandler(filters.TEXT & ~filters.COMMAND, obtener_personas)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)
application.add_handler(conv)

@app_flask.route("/")
def home():
    return "RESERVAMX corriendo"

@app_flask.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def telegram_webhook():
    print(">>> Webhook recibió algo")
    update = telegram.Update.de_json(request.get_json(force=True), application.bot)
    async def process():
        await application.initialize()   # <--- ESTA LÍNEA ES CLAVE
        await application.process_update(update)

    asyncio.run(process())
    return "OK"

if __name__ == "__main__":
    app_flask.run(host="0.0.0.0", port=3000)



