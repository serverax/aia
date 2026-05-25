import re
import sqlite3
from datetime import datetime

from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

DB_FILE = "waitlist.db"


def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        """CREATE TABLE IF NOT EXISTS waitlist
    (id INTEGER PRIMARY KEY, name TEXT, email TEXT UNIQUE, 
     profession TEXT, company TEXT, created_at TIMESTAMP)"""
    )
    conn.commit()
    conn.close()


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy"})


@app.route("/api/waitlist/join", methods=["POST"])
def join_waitlist():
    try:
        data = request.get_json()
        name = data.get("name", "").strip()
        email = data.get("email", "").strip()
        profession = data.get("profession", "").strip()
        company = data.get("company", "").strip()

        if not all([name, email, profession]):
            return jsonify({"status": "error", "message": "Missing fields"}), 400

        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(pattern, email):
            return jsonify({"status": "error", "message": "Invalid email"}), 400

        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        try:
            c.execute(
                "INSERT INTO waitlist (name, email, profession, company, created_at) VALUES (?,?,?,?,?)",
                (name, email, profession, company, datetime.now()),
            )
            conn.commit()
            c.execute("SELECT COUNT(*) FROM waitlist WHERE id <= last_insert_rowid()")
            position = c.fetchone()[0]
        except sqlite3.IntegrityError:
            conn.close()
            return jsonify({"status": "error", "message": "Email already registered"}), 409

        conn.close()
        print(f"✅ New signup: {name} ({email}) - Position #{position}")

        return jsonify({"status": "success", "position": position, "email": email}), 201
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/waitlist/count", methods=["GET"])
def get_count():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM waitlist")
    count = c.fetchone()[0]
    conn.close()
    return jsonify({"status": "success", "count": count})


@app.route("/api/waitlist/list", methods=["GET"])
def list_waitlist():
    api_key = request.headers.get("X-API-Key")
    if api_key != "admin-key-change":
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        "SELECT id, name, email, profession, company, created_at FROM waitlist ORDER BY created_at DESC"
    )
    rows = c.fetchall()
    conn.close()

    users = [
        {
            "id": r[0],
            "name": r[1],
            "email": r[2],
            "profession": r[3],
            "company": r[4],
            "joined": r[5],
        }
        for r in rows
    ]
    return jsonify({"status": "success", "count": len(users), "users": users})


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
