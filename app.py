import datetime
from flask import Flask, request, jsonify
from pymongo import MongoClient
from flask_cors import CORS
import requests
import os
from dotenv import load_dotenv
load_dotenv()


app = Flask(__name__)

CORS(app, origins=["http://localhost:3000"])

API_KEY = os.getenv("API_KEY")
MONGO_URI = os.getenv("MONGO_URI")

mongo_client = MongoClient(os.environ.get("MONGO_URI"))
db = mongo_client["psyconnect"]

students_col    = db["students"]
mentors_col     = db["mentors"]
psychologists_col = db["psychologists"]
users_col       = db["users"]
diary_col       = db["diary"]
chats_col       = db["mentor_chats"]
sessions_col    = db["session_requests"]
notifs_col      = db["notifications"]


# ── HEALTH CHECK ──────────────────────────────────────────
@app.route('/')
def home():
    return "PsyConnect Backend Running"


# ── HOME DATA ─────────────────────────────────────────────
@app.route('/home-data', methods=['GET'])
def home_data():
    return jsonify({
        "students":      students_col.count_documents({}),
        "mentors":       list(mentors_col.find({}, {"_id": 0})),
        "psychologists": list(psychologists_col.find({}, {"_id": 0})),
    })


# ── SIGNUP ────────────────────────────────────────────────
@app.route('/signup', methods=['POST'])
def signup():
    data    = request.json
    role    = data.get("role")
    role_id = data.get("roleId")

    if role == "student":
        existing = students_col.find_one({"studentId": role_id})
    elif role == "mentor":
        existing = mentors_col.find_one({"mentorId": role_id})
    else:
        existing = psychologists_col.find_one({"psychologistId": role_id})

    if not existing:
        return jsonify({"success": False, "message": "ID not found in college database"})

    users_col.update_one({"roleId": role_id}, {"$set": data}, upsert=True)
    return jsonify({"success": True})


# ── LOGIN ─────────────────────────────────────────────────
@app.route('/login', methods=['POST'])
def login():
    data     = request.json
    user_id  = data.get("userId", "").strip()
    password = data.get("password", "").strip()

    # Student: password = rollNo
    try:
        student = students_col.find_one({
            "studentId": user_id,
            "rollNo": int(password)
        })
    except ValueError:
        student = None

    if student:
        student["_id"] = str(student["_id"])
        return jsonify({"role": "student", "data": student})

    # Mentor: just check mentorId exists (add password later)
    mentor = mentors_col.find_one({"mentorId": user_id.upper()})
    if mentor:
        mentor["_id"] = str(mentor["_id"])
        return jsonify({"role": "mentor", "data": mentor})

    # Psychologist
    therapist = psychologists_col.find_one({"psychologistId": user_id.upper()})
    if therapist:
        therapist["_id"] = str(therapist["_id"])
        return jsonify({"role": "psychologist", "data": therapist})

    return jsonify({"message": "Invalid credentials"}), 401


# ── STUDENT PROFILE ───────────────────────────────────────
@app.route('/student/<path:student_id>', methods=['GET'])
def get_student(student_id):
    s = students_col.find_one({"studentId": student_id})
    if s:
        s["_id"] = str(s["_id"])
    return jsonify(s or {})


# ── MENTOR + ASSIGNED STUDENTS ────────────────────────────
@app.route('/mentor/<path:mentor_id>', methods=['GET'])
def get_mentor(mentor_id):
    m = mentors_col.find_one({"mentorId": mentor_id.upper()})
    if m:
        m["_id"] = str(m["_id"])

    # Extract mentor number e.g. MENTOR01 → 1
    try:
        num = int(''.join(filter(str.isdigit, mentor_id)))
    except ValueError:
        num = 1

    start = (num - 1) * 20 + 1
    end   = num * 20
    students = list(students_col.find(
        {"rollNo": {"$gte": start, "$lte": end}}, {"_id": 0}
    ))
    return jsonify({"mentor": m, "students": students})


# ── PSYCHOLOGIST + ASSIGNED STUDENTS ─────────────────────
@app.route('/psychologist/<path:psych_id>', methods=['GET'])
def get_psychologist(psych_id):
    p = psychologists_col.find_one({"psychologistId": psych_id.upper()})
    if p:
        p["_id"] = str(p["_id"])

    if "01" in psych_id:
        students = list(students_col.find({"rollNo": {"$gte": 1,   "$lte": 100}}, {"_id": 0}))
    else:
        students = list(students_col.find({"rollNo": {"$gte": 101, "$lte": 200}}, {"_id": 0}))

    return jsonify({"psychologist": p, "students": students})


# ── CHATBOT ───────────────────────────────────────────────
@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.json
        messages = data.get("messages", [])

        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "openrouter/auto",
                "messages": messages
            }
        )

        result = response.json()
        print("RESPONSE:", result)

        if "choices" in result:
            reply = result["choices"][0]["message"]["content"]
        else:
            reply = result.get("error", {}).get("message", "Error 😅")

        return jsonify({"reply": reply})

    except Exception as e:
        print("ERROR:", e)
        return jsonify({"reply": "Server error ❌"})
    

  
# print("API KEY:", os.environ.get("GEMINI_API_KEY"))
# @app.route("/chat", methods=["POST"])
# def chat():
#     try:
#         data = request.json
#         messages = data.get("messages", [])

#         conversation = ""
#         for m in messages:
#             if m["role"] == "user":
#                 conversation += f"User: {m['content']}\n"
#             else:
#                 conversation += f"Assistant: {m['content']}\n"

#         prompt = f"""
#         You are PsyConnect AI — a mental wellness assistant.
#         Be calm, supportive, empathetic.

#         {conversation}
#         """

#         response = ai_client.models.generate_content(
#             model="gemini-2.0-flash",
#             contents=prompt
#         )

#         return jsonify({"reply": response.text})

#     except Exception as e:
#         print("ERROR:", e)
#         return jsonify({"reply": "AI error: " + str(e)})
    

# ── DIARY ─────────────────────────────────────────────────
@app.route('/diary/<path:student_id>', methods=['GET'])
def get_diary(student_id):
    entries = list(diary_col.find(
        {"studentId": student_id}, {"_id": 0}
    ).sort("_id", -1))
    return jsonify({"entries": entries})

@app.route('/diary', methods=['POST'])
def save_diary():
    diary_col.insert_one(request.json)
    return jsonify({"success": True})


# ── MENTOR CHAT ───────────────────────────────────────────
@app.route('/mentor-chat/<path:student_id>', methods=['GET'])
def get_mentor_chat(student_id):
    msgs = list(chats_col.find(
        {"studentId": student_id}, {"_id": 0}
    ).sort("_id", 1))
    return jsonify({"messages": msgs})

@app.route('/mentor-chat', methods=['POST'])
def post_mentor_chat():
    chats_col.insert_one(request.json)
    return jsonify({"success": True})


# ── NOTIFICATIONS ─────────────────────────────────────────
@app.route('/notifications/<path:recipient_id>', methods=['GET'])
def get_notifications(recipient_id):
    notifs = list(notifs_col.find(
        {"recipientId": recipient_id}, {"_id": 0}
    ).sort("_id", -1))
    return jsonify({"notifications": notifs})

@app.route('/notifications', methods=['POST'])
def post_notification():
    data = request.json
    data["read"] = False
    notifs_col.insert_one(data)
    return jsonify({"success": True})


# ── SESSION REQUESTS ──────────────────────────────────────
@app.route('/session-request', methods=['POST'])
def session_request():
    data = request.json
    data["date"] = str(datetime.datetime.now())
    sessions_col.insert_one(data)

    # Notify the psychologist
    psych_id = students_col.find_one(
        {"studentId": data.get("studentId")}, {"_id": 0, "psychologistId": 1}
    )
    if psych_id:
        notifs_col.insert_one({
            "recipientId": psych_id["psychologistId"],
            "subject":     f"Session Request from {data.get('studentName', data.get('studentId'))}",
            "message":     data.get("headline", ""),
            "date":        str(datetime.datetime.now()),
            "read":        False,
        })
    return jsonify({"success": True})

@app.route('/session-requests/<path:psych_id>', methods=['GET'])
def get_session_requests(psych_id):
    reqs = list(sessions_col.find({}, {"_id": 0}))
    return jsonify({"requests": reqs})


# ── SEND SCHEDULE ─────────────────────────────────────────
@app.route('/send-schedule', methods=['POST'])
def send_schedule():
    data = request.json
    notifs_col.insert_one({
        "recipientId": data["studentId"],
        "subject":     f"Session Scheduled: {data.get('headline', '')}",
        "message":     (
            f"{data.get('location', 'Ground Floor, Admin Office, SLRTCE')} | "
            f"{data.get('day', '')}, {data.get('date', '')} | "
            f"{data.get('time', '')} | "
            f"{data.get('notes', '')}"
        ),
        "date":  str(datetime.datetime.now()),
        "read":  False,
    })
    return jsonify({"success": True})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)