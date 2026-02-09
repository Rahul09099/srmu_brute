import os
import telebot
import time
import requests
from app import send_otps, otp_tracker

# Get token from environment variable (Best for hosting like Render)
API_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')

bot = telebot.TeleBot(API_TOKEN)

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "Welcome! Use /send <phone1,phone2,...> <count> to send OTPs.\nExample: /send 9876543210,1234567890 5")

@bot.message_handler(commands=['send'])
def handle_send_otp(message):
    try:
        # Split command and arguments
        args = message.text.split()
        if len(args) < 3:
            bot.reply_to(message, "Usage: /send <phone1,phone2,...> <count>")
            return

        phones_raw = args[1]
        otp_count_raw = args[2]

        # Parse OTP count
        try:
            otp_count = int(otp_count_raw)
            if otp_count <= 0:
                raise ValueError
        except ValueError:
            bot.reply_to(message, "OTP count must be a positive number.")
            return

        # Parse phone numbers
        numbers = [
            n.strip() for n in phones_raw.split(",")
            if n.strip().isdigit()
        ]

        if not numbers:
            bot.reply_to(message, "Invalid phone numbers provided.")
            return

        bot.reply_to(message, f"🚀 Starting OTP blast for {len(numbers)} number(s)...")

        # Call the shared logic from srmu.py
        results = send_otps(numbers, otp_count)

        # Build response message
        response_lines = ["✅ OTP Sending Complete:"]
        for res in results:
            response_lines.append(f"📱 {res['phone']}: {res['status']} (Sent: {res['sent_now']}, Total: {res['total_sent']})")
        
        bot.reply_to(message, "\n".join(response_lines))

    except Exception as e:
        bot.reply_to(message, f"❌ An error occurred: {str(e)}")

@bot.message_handler(commands=['status'])
def handle_status(message):
    if not otp_tracker:
        bot.reply_to(message, "No activity tracked yet.")
        return
    
    status_msg = "📊 OTP Status Tracker:\n"
    for phone, total in otp_tracker.items():
        status_msg += f"📱 {phone}: {total} total OTPs sent\n"
    
    bot.reply_to(message, status_msg)

if __name__ == "__main__":
    print("Bot is starting...")
    bot.infinity_polling()
