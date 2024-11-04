from flask import Flask, jsonify, request
import json
import threading
import time
import uuid
import os
import random
import string
import requests  # নিজে নিজেকে রিকোয়েস্ট পাঠানোর জন্য

app = Flask(__name__)

# JSON ফাইল থেকে ডেটা লোড করা
def load_data(filename):
    if not os.path.exists(filename):
        with open(filename, 'w') as file:
            if filename == 'price.json':
                # প্রাথমিকভাবে price.json ফাইলে সংখ্যা 3 রাখা
                json.dump(3, file)
            else:
                json.dump([], file)
    with open(filename, 'r') as file:
        return json.load(file)

# JSON ফাইলে ডেটা সেভ করা
def save_data(filename, data):
    with open(filename, 'w') as file:
        json.dump(data, file, indent=4)

# ইউনিক আইডি জেনারেটর (আপডেটেড)
def generate_unique_id():
    existing_ids = set()
    # বিদ্যমান সব ID সংগ্রহ করা
    for filename in ['gmail.json', 'status.json', 'failed.json', 'completed.json']:
        data = load_data(filename)
        existing_ids.update(entry.get("Gmail No") for entry in data if "Gmail No" in entry)

    while True:
        letters_part = ''.join(random.choices(string.ascii_uppercase, k=2))
        first_digits_part = ''.join(random.choices(string.digits, k=11))
        second_digits_part = ''.join(random.choices(string.digits, k=2))
        unique_id = f"{letters_part}-{first_digits_part}-{second_digits_part}"
        if unique_id not in existing_ids:
            return unique_id
        # যদি ID ইতোমধ্যে থাকে, নতুন করে জেনারেট করুন

# gmail.json এ জিমেইল আছে কিনা চেক করা
def is_gmail_exists(gmail):
    gmail_data = load_data('gmail.json')
    status_data = load_data('status.json')
    failed_data = load_data('failed.json')
    completed_data = load_data('completed.json')
    return any(entry["gmail"] == gmail for entry in (gmail_data + status_data + failed_data + completed_data))

# /gmail রুট থেকে JSON ডেটা দেখানো এবং নতুন ডেটা যোগ করা
@app.route('/gmail', methods=['GET'])
def manage_gmail():
    add_gmail = request.args.get('add')
    add_password = request.args.get('pass')

    if not add_gmail or not add_password:
        data = load_data('gmail.json')
        return jsonify(data)

    if is_gmail_exists(add_gmail):
        return jsonify({"error": "This Gmail already exists in the server."}), 400

    data = load_data('gmail.json')
    new_entry = {
        "Gmail No": generate_unique_id(),
        "gmail": add_gmail,
        "password": add_password
    }
    data.append(new_entry)
    save_data('gmail.json', data)

    return jsonify({"message": "Gmail added successfully", "Gmail No": new_entry["Gmail No"], "gmail": add_gmail, "password": add_password}), 200

# /status রুট থেকে status.json ডেটা দেখানো এবং স্ট্যাটাস আপডেট করা
@app.route('/status', methods=['GET'])
def show_or_update_status():
    email = request.args.get('email')
    new_status = request.args.get('exchange')

    valid_statuses = ["RUNNING", "COMPLETED", "CANCEL", "FAILED"]

    if not email or not new_status:
        data = load_data('status.json')
        return jsonify(data)

    if new_status.upper() not in valid_statuses:
        return jsonify({"error": "Invalid status. Choose from RUNNING, COMPLETED, CANCEL, FAILED"}), 400

    status_data = load_data('status.json')
    entry = next((item for item in status_data if item["gmail"] == email), None)

    if not entry:
        return jsonify({"error": "Gmail not found in status.json"}), 404

    entry["gmail_status"] = new_status.upper()
    entry["status_updated_at"] = time.time()  # স্ট্যাটাস আপডেট সময় সেভ করা
    save_data('status.json', status_data)

    return jsonify({"message": "Status updated successfully", "gmail": email, "new_status": entry["gmail_status"]}), 200

# /gmail_remove রুট থেকে নির্দিষ্ট Gmail মুছে ফেলা
@app.route('/gmail_remove', methods=['GET'])
def remove_gmail():
    remove_gmail = request.args.get('gmail')
    if not remove_gmail:
        return jsonify({"error": "Please provide a Gmail to remove"}), 400

    data = load_data('gmail.json')
    new_data = [entry for entry in data if entry["gmail"] != remove_gmail]

    if len(new_data) == len(data):
        return jsonify({"error": "Gmail not found"}), 404

    save_data('gmail.json', new_data)
    return jsonify({"message": "Gmail removed successfully", "gmail": remove_gmail}), 200

# /gmail_transfer রুট থেকে নির্দিষ্ট Gmail ট্রান্সফার করা
@app.route('/gmail_transfer', methods=['GET'])
def transfer_gmail():
    transfer_gmail = request.args.get('gmail')
    user_id = request.args.get('user_id')
    user_name = request.args.get('user_name')

    if not transfer_gmail or not user_id or not user_name:
        return jsonify({"error": "Please provide gmail, user_id, and user_name"}), 400

    if not is_gmail_exists(transfer_gmail):
        return jsonify({"error": "Gmail not found in gmail.json"}), 404

    gmail_data = load_data('gmail.json')
    entry = next((item for item in gmail_data if item["gmail"] == transfer_gmail), None)

    status_data = load_data('status.json')
    transfer_entry = {
        "Gmail No": entry["Gmail No"],
        "gmail": entry["gmail"],
        "password": entry["password"],
        "user_id": user_id,
        "user_name": user_name,
        "gmail_status": "RUNNING",
        "status_updated_at": time.time()  # স্ট্যাটাস আপডেটের সময়
    }
    status_data.append(transfer_entry)
    save_data('status.json', status_data)

    new_gmail_data = [item for item in gmail_data if item["gmail"] != transfer_gmail]
    save_data('gmail.json', new_gmail_data)

    return jsonify({"message": "Gmail transferred successfully", "gmail": transfer_gmail, "user_id": user_id, "user_name": user_name}), 200

# /failed এবং /completed রুট থেকে failed.json ও completed.json এর তথ্য দেখানো
@app.route('/failed', methods=['GET'])
def show_failed():
    data = load_data('failed.json')
    return jsonify(data)

@app.route('/completed', methods=['GET'])
def show_completed():
    data = load_data('completed.json')
    return jsonify(data)

# CANCEL, RUNNING এবং FAILED স্ট্যাটাসের জিমেইলগুলো ফেরত আনার জন্য ব্যাকগ্রাউন্ড ফাংশন
def monitor_status_and_transfer_emails():
    while True:
        status_data = load_data('status.json')
        gmail_data = load_data('gmail.json')
        failed_data = load_data('failed.json')
        completed_data = load_data('completed.json')
        current_time = time.time()

        updated_status_data = []
        for entry in status_data:
            time_elapsed = current_time - entry["status_updated_at"]

            # CANCEL স্ট্যাটাসের মেইল ২ মিনিট পর ফেরত আনা
            if entry["gmail_status"] == "CANCEL" and time_elapsed >= 120:
                gmail_data.append({
                    "Gmail No": entry["Gmail No"],
                    "gmail": entry["gmail"],
                    "password": entry["password"]
                })
            # RUNNING স্ট্যাটাসের মেইল ১ মিনিট পর ফেরত আনা
            elif entry["gmail_status"] == "RUNNING" and time_elapsed >= 60:
                gmail_data.append({
                    "Gmail No": entry["Gmail No"],
                    "gmail": entry["gmail"],
                    "password": entry["password"]
                })
            # FAILED স্ট্যাটাসের মেইল ৫ মিনিট পর failed.json এ স্থানান্তর করা
            elif entry["gmail_status"] == "FAILED" and time_elapsed >= 300:
                entry["failed_at"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(current_time))
                failed_data.append(entry)
            # COMPLETED স্ট্যাটাসের মেইল সাথে সাথে completed.json এ স্থানান্তর করা
            elif entry["gmail_status"] == "COMPLETED":
                entry["completed_at"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(current_time))
                completed_data.append(entry)
            else:
                updated_status_data.append(entry)  # এখনও status.json এ রাখুন

        save_data('status.json', updated_status_data)
        save_data('gmail.json', gmail_data)
        save_data('failed.json', failed_data)
        save_data('completed.json', completed_data)

        time.sleep(60)  # প্রতি এক মিনিটে চেক করা

# /price রুট থেকে প্রাইস দেখানো এবং আপডেট করা
@app.route('/price', methods=['GET'])
def manage_price():
    add_price = request.args.get('add')
    data = load_data('price.json')

    if add_price:
        try:
            # যদি add_price একটি সংখ্যা হয়, সেটি সেভ করা হবে
            price = float(add_price)
            # নতুন প্রাইস price.json এ সেভ করা
            save_data('price.json', price)
            return jsonify({"message": "Price updated successfully", "price": price}), 200
        except ValueError:
            return jsonify({"error": "Invalid price value"}), 400
    else:
        # যদি 'add' প্যারামিটার না দেওয়া হয়, price.json এর ডেটা দেখানো হবে
        return jsonify({"price": data})

# /alive রুট তৈরি করা
@app.route('/alive', methods=['GET'])
def alive():
    return jsonify({"status": "I'm alive"}), 200

# প্রতি ৫ মিনিট অন্তর নিজেকে /alive রিকোয়েস্ট পাঠানোর ব্যাকগ্রাউন্ড ফাংশন
def keep_alive():
    while True:
        try:
            # আপনার সার্ভারের হোস্ট এবং পোর্ট অনুযায়ী URL পরিবর্তন করুন
            requests.get('https://nekotoolsarver.onrender.com/alive')
            print("Sent /alive request to keep the app alive.")
        except Exception as e:
            print(f"Error sending /alive request: {e}")
        time.sleep(300)  # প্রতি ৫ মিনিটে (300 সেকেন্ড) চেক করা

# ব্যাকগ্রাউন্ডে চেকিং ফাংশন চালানো
background_thread = threading.Thread(target=monitor_status_and_transfer_emails, daemon=True)
background_thread.start()

# ব্যাকগ্রাউন্ডে keep_alive ফাংশন চালানো
keep_alive_thread = threading.Thread(target=keep_alive, daemon=True)
keep_alive_thread.start()

# /balance এন্ডপয়েন্ট থেকে balance.json এর ডেটা দেখানো এবং নতুন ইউজার যোগ করা
@app.route('/balance', methods=['GET'])
def manage_balance():
    user_id = request.args.get('user_id')
    tg_username = request.args.get('tg_user')
    user_name = request.args.get('user_name')

    if not user_id or not tg_username or not user_name:
        # প্যারামিটার না থাকলে balance.json এর ডেটা দেখানো
        data = load_data('balance.json')
        return jsonify(data)

    # চেক করা ইউজার আছে কিনা
    balance_data = load_data('balance.json')
    existing_user = next((item for item in balance_data if item["user_id"] == user_id), None)
    if existing_user:
        return jsonify({"error": "User already exists"}), 400

    # নতুন ইউজার যোগ করা
    new_user = {
        "user_name": user_name,
        "user_id": user_id,
        "tg_user": tg_username,
        "available_balance": 0,
        "pending_withdraw": 0,
        "already_withdraw": 0
    }
    balance_data.append(new_user)
    save_data('balance.json', balance_data)

    return jsonify({"message": "User added successfully", "user": new_user}), 200

# /balance_update এন্ডপয়েন্ট থেকে ইউজারের ব্যালেন্স আপডেট করা
@app.route('/balance_update', methods=['GET'])
def update_balance():
    user_id = request.args.get('user_id')
    update_field = request.args.get('for')
    value = request.args.get('value')

    if not user_id or not update_field or value is None:
        return jsonify({"error": "Please provide user_id, for, and value parameters"}), 400

    try:
        value = float(value)
    except ValueError:
        return jsonify({"error": "Value must be a number"}), 400

    if value < 0:
        return jsonify({"error": "Value must be non-negative"}), 400

    balance_data = load_data('balance.json')
    user = next((item for item in balance_data if item["user_id"] == user_id), None)
    if not user:
        return jsonify({"error": "User not found"}), 404

    if update_field == "available_balance":
        user["available_balance"] += value
        message = "Available balance updated successfully"
    elif update_field == "pending_withdraw":
        if user["available_balance"] >= value:
            user["available_balance"] -= value
            user["pending_withdraw"] += value
            message = "Pending withdraw updated successfully"
        else:
            return jsonify({"error": "Insufficient available balance"}), 400
    elif update_field == "already_withdraw":
        if user["pending_withdraw"] >= value:
            user["pending_withdraw"] -= value
            user["already_withdraw"] += value
            message = "Already withdraw updated successfully"
        else:
            return jsonify({"error": "Insufficient pending withdraw balance"}), 400
    else:
        return jsonify({"error": "Invalid field to update. Choose from available_balance, pending_withdraw, already_withdraw"}), 400

    save_data('balance.json', balance_data)
    return jsonify({"message": message, "user": user}), 200

if __name__ == '__main__':
    # প্রাথমিকভাবে price.json এ সংখ্যা 3 সেট করা
    if not os.path.exists('price.json'):
        save_data('price.json', 3)
    app.run(host='0.0.0.0', port=81)
