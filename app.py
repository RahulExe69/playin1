import os
import time
import random
import string
import logging
import threading
from flask import Flask, request, jsonify, render_template
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# --- Configuration & Logging ---
logging.basicConfig(
    filename='account_creator.log',
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s'
)

SIGNUP_URL = os.environ.get("SIGNUP_URL", "https://playinexch247.com/#")
DELAY_SECONDS = int(os.environ.get("DELAY_SECONDS", "5"))

# --- Global Status ---
status = {
    "running": False,
    "base_username": "",
    "total": 0,
    "created": 0,
    "success": 0,
    "failure": 0
}
status_lock = threading.Lock()

def create_accounts(base, password, count, custom_phone):
    global status
    with status_lock:
        status.update({
            "running": True,
            "base_username": base,
            "total": count,
            "created": 0,
            "success": 0,
            "failure": 0
        })

    driver_opts = Options()
    driver_opts.add_argument("--headless")
    driver_opts.add_argument("--disable-gpu")
    driver_opts.add_argument("--no-sandbox")
    driver_opts.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(ChromeDriverManager().install(), options=driver_opts)

    for i in range(1, count + 1):
        username = f"{base}{i}"
        email = f"{base}{i}@gmail.com"
        phone = custom_phone or "".join(random.choices(string.digits, k=10))
        success_flag = False
        try:
            driver.get(SIGNUP_URL)
            driver.find_element(By.NAME, "username").send_keys(username)
            driver.find_element(By.NAME, "email").send_keys(email)
            driver.find_element(By.NAME, "password").send_keys(password)
            driver.find_element(By.NAME, "mobile").send_keys(phone)
            driver.find_element(By.XPATH, "//button[@type='submit']").click()
            logging.info(f"[OK]   {username} / {email} / {phone}")
            success_flag = True
        except Exception as e:
            logging.error(f"[FAIL] {username}: {e}")

        with status_lock:
            status["created"] += 1
            if success_flag:
                status["success"] += 1
            else:
                status["failure"] += 1

        time.sleep(DELAY_SECONDS)

    driver.quit()
    with status_lock:
        status["running"] = False
    logging.info(f"Finished batch: {status['success']}/{status['total']} created.")

# --- Flask App & Routes ---
app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    error = success_msg = None
    if request.method == "POST":
        base = request.form.get("base_username", "").strip()
        password = request.form.get("password", "").strip()
        count_str = request.form.get("count", "").strip()
        phone = request.form.get("phone", "").strip()

        if not base or not password or not count_str:
            error = "Base username, password, and count are required."
        elif not count_str.isdigit() or int(count_str) < 1:
            error = "Count must be a positive integer."
        elif phone and (not phone.isdigit() or len(phone) != 10):
            error = "Phone must be a 10-digit number."
        else:
            count = int(count_str)
            thread = threading.Thread(target=create_accounts, args=(base, password, count, phone), daemon=True)
            thread.start()
            success_msg = f"Started batch: base='{base}', count={count}, delay={DELAY_SECONDS}s"

    return render_template("index.html", error=error, success=success_msg)

@app.route("/status", methods=["GET"])
def get_status():
    with status_lock:
        return jsonify(status)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
