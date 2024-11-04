from flask import Flask, jsonify, request
import json
import threading
import time
import uuid
import os
import random
import string

app = Flask(__name__)

# JSON ফাইল থেকে ডেটা লোড করা
def load_data(filename):
    if not os.path.exists(filename):
        with open(filename, 'w') as file:
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

# ব্যাকগ্রাউন্ডে চেকিং ফাংশন চালানো
background_thread = threading.Thread(target=monitor_status_and_transfer_emails, daemon=True)
background_thread.start()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=81)