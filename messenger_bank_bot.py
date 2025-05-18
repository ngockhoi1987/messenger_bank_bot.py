from flask import Flask, request
import requests, random, time

app = Flask(__name__)

# === ĐIỀN TOKEN CỦA BẠN Ở ĐÂY ===
VERIFY_TOKEN = "mySuperSecretToken123"
PAGE_ACCESS_TOKEN = "EAAfALhUeIpoBO614HYFkT3t0SfZAuqZAfNY4ZACusoEciFrQW06VmdigNjRWIZCCZB0itcpEyTVqGhsn55vJpTRvpgDJIJzG4IOL2dholW2gnwRKwynVVpXxH3PWdNZBiyPZBci7LsEQMt3JAhtI6qbD1MvQSKgUQoT6VpyE8bpMd72GOmT7IBH4j6VQEp9jAt3ID0dFnYgpikqLelMbBHtobcsNQZDZD"
# ================================

users = {}
debts = {}
last_game_time = {}

def send_message(recipient_id, text):
    url = "https://graph.facebook.com/v17.0/me/messages"
    params = {"access_token": PAGE_ACCESS_TOKEN}
    headers = {"Content-Type": "application/json"}
    body = {
        "recipient": {"id": recipient_id},
        "message": {"text": text}
    }
    requests.post(url, params=params, json=body, headers=headers)

def create_account(uid, name):
    if uid in users:
        return False
    taken = {u["account"] for u in users.values()}
    acc = next(i for i in range(1, 101) if i not in taken)
    users[uid] = {"name": name, "balance": 100_000_000, "account": acc}
    debts[uid] = 0
    return True

@app.route("/", methods=["GET"])
def root():
    return "Messenger Bank Bot is running."

@app.route("/webhook", methods=["GET","POST"])
def webhook():
    if request.method == "GET":
        token = request.args.get("hub.verify_token")
        if token == VERIFY_TOKEN:
            return request.args.get("hub.challenge")
        return "Verification token mismatch", 403

    data = request.json
    for entry in data.get("entry", []):
        for ev in entry.get("messaging", []):
            uid = ev["sender"]["id"]
            if "message" in ev and "text" in ev["message"]:
                text = ev["message"]["text"].strip()
                handle(uid, text)
    return "ok", 200

def handle(uid, txt):
    parts = txt.split()
    cmd = parts[0].lower()
    args = parts[1:]

    # Tạo tài khoản
    if cmd == "!tao":
        name = " ".join(args) if args else f"User{uid[-4:]}"
        if create_account(uid, name):
            acc = users[uid]["account"]
            send_message(uid, f"✅ Tạo tài khoản thành công!\nTên: {name}\nSTK: {acc}\nSố dư: 100,000,000$")
        else:
            send_message(uid, "❌ Bạn đã có tài khoản rồi.")
        return

    # Chưa có tài khoản
    if uid not in users:
        send_message(uid, "❌ Bạn chưa có tài khoản! Dùng !tao <tên> để tạo.")
        return

    user = users[uid]

    if cmd == "!bank":
        send_message(uid, f"💰 Số dư hiện tại: {user['balance']:,}$")

    elif cmd == "!vay" and args:
        amt = int(args[0].replace(",", ""))
        if debts[uid] > 0:
            send_message(uid, "⚠️ Bạn còn nợ cũ, phải trả hết trước khi vay mới.")
        elif 10_000_000 <= amt <= 1_000_000_000:
            debt = int(amt * 1.1)
            user["balance"] += amt
            debts[uid] = debt
            send_message(uid, f"✅ Đã vay {amt:,}$. Nợ cần trả: {debt:,}$.")
        else:
            send_message(uid, "❌ Số tiền vay phải từ 10 triệu đến 1 tỷ.")
    
    elif cmd == "!travay":
        if debts[uid] == 0:
            send_message(uid, "✅ Bạn không có nợ.")
        elif args and args[0].lower() == "all":
            if user["balance"] >= debts[uid]:
                user["balance"] -= debts[uid]
                send_message(uid, f"✅ Trả hết nợ {debts[uid]:,}$.")
                debts[uid] = 0
            else:
                send_message(uid, "❌ Không đủ tiền để trả hết nợ.")
        elif args:
            pay = int(args[0])
            pay = min(pay, debts[uid])
            if user["balance"] >= pay:
                user["balance"] -= pay
                debts[uid] -= pay
                send_message(uid, f"✅ Đã trả {pay:,}$. Nợ còn lại: {debts[uid]:,}$.")
            else:
                send_message(uid, "❌ Không đủ tiền để trả.")
        else:
            send_message(uid, "❌ Cú pháp: !travay all hoặc !travay <số tiền>")

    elif cmd == "!chuyen" and len(args)==2:
        to_acc = int(args[0])
        amt = int(args[1])
        if amt>0 and user["balance"]>=amt:
            dest = next((k for k,v in users.items() if v["account"]==to_acc), None)
            if dest:
                user["balance"] -= amt
                users[dest]["balance"] += amt
                send_message(uid, f"✅ Chuyển {amt:,}$ đến STK {to_acc}.")
            else:
                send_message(uid, "❌ Không tìm thấy STK đó.")
        else:
            send_message(uid, "❌ Số dư không đủ hoặc sai cú pháp.")

    elif cmd == "!tx" and len(args)==2:
        choice = args[0].lower()
        bet = int(args[1])
        if choice in ("tài","xỉu") and user["balance"]>=bet:
            dice = [random.randint(1,6) for _ in range(3)]
            total = sum(dice)
            res = "tài" if total>10 else "xỉu"
            win = (choice==res)
            user["balance"] += bet if win else -bet
            send_message(uid, f"🎲 {dice}={total} => {res.upper()}\nBạn {'🏆 thắng' if win else '💔 thua'} {bet:,}$.")
        else:
            send_message(uid, "❌ Cú pháp: !tx tài/xỉu <số tiền> hoặc không đủ số dư.")

    elif cmd == "!game":
        now = time.time()
        last = last_game_time.get(uid,0)
        if now-last<300:
            send_message(uid, f"⏳ Chờ {int(300-(now-last))}s để chơi lại.")
        else:
            last_game_time[uid]=now
            games = "\\n".join([
                "1: Đào vàng ⛏️","2: Đào kim cương 💎","3: Đào mỏ ⛏️","4: Đóng tàu 🚢",
                "5: Làm thuê 🛠️","6: Làm việc 💼","7: Đánh thuê 🥊","8: Bán hàng 🛒",
                "9: Cướp ngân hàng 🏦","10: Tiền miễn phí 🎁"
            ])
            send_message(uid, "🎮 Chọn số 1–10 để chơi game:\\n"+games)

    elif cmd.isdigit() and 1<=int(cmd)<=10 and uid in last_game_time:
        reward = random.randint(10_000,1_000_000)
        user["balance"] += reward
        send_message(uid, f"🎉 Bạn nhận được {reward:,}$! Số dư: {user['balance']:,}$")

    else:
        send_message(uid, "❓ Lệnh không hợp lệ. Xem !help để biết các lệnh.")

@app.route("/help", methods=["GET"])
def help_page():
    return (
        "!tao <tên>  – tạo tài khoản\\n"
        "!bank       – kiểm tra số dư\\n"
        "!vay <số>   – vay tiền\\n"
        "!travay all/<số> – trả nợ\\n"
        "!chuyen <stk> <số> – chuyển tiền\\n"
        "!tx tài/xỉu <số> – chơi tài xỉu\\n"
        "!game       – chơi mini-game\\n"
        "1–10         – chọn game sau !game"
    )

if __name__=="__main__":
    app.run(host="0.0.0.0", port=8080)
