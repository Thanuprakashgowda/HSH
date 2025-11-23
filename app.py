from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import mysql.connector
import jwt
import datetime
import os

# ================== CONFIG ==================

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "2301",            # Your MySQL password
    "database": "hostelhub",
}

# ✅ Correct JWT key (removed extra 's')
JWT_SECRET = "f3c1f0e8b76d4c0fa93f1d4b28c697f7e7c43a28db1ff2b29b78adcc24ff9b60"
JWT_ALGORITHM = "HS256"

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ================== APP INIT ==================

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
CORS(app)


# ================== DB HELPER ==================

def get_db():
    conn = mysql.connector.connect(**DB_CONFIG)
    return conn


# ================== AUTH HELPERS ==================

def create_token(user):
    payload = {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "role": user["role"],
        "exp": datetime.datetime.utcnow() + datetime.timedelta(days=1),
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    if isinstance(token, bytes):
        token = token.decode("utf-8")
    return token


def decode_token(token):
    try:
        data = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return data
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def token_required(f):
    from functools import wraps

    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", None)
        if not auth_header:
            return jsonify({"message": "Authorization header missing"}), 401

        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return jsonify({"message": "Invalid token format"}), 401

        token = parts[1]
        data = decode_token(token)
        if not data:
            return jsonify({"message": "Invalid or expired token"}), 401

        request.user = data
        return f(*args, **kwargs)

    return decorated


def admin_required(f):
    from functools import wraps

    @wraps(f)
    @token_required
    def decorated(*args, **kwargs):
        user = request.user
        if user.get("role") != "admin":
            return jsonify({"message": "Admins only"}), 403
        return f(*args, **kwargs)

    return decorated


# ================== ROUTES ==================

@app.route("/")
def health():
    return jsonify({"message": "HostelHub Flask backend running"})


# ------- AUTH --------

@app.route("/auth/register", methods=["POST"])
def register():
    data = request.get_json()
    if not data:
        return jsonify({"message": "JSON body required"}), 400

    name = data.get("name")
    email = data.get("email")
    password = data.get("password")
    role = data.get("role", "student")

    if not name or not email or not password:
        return jsonify({"message": "Name, email and password are required"}), 400

    if role not in ["student", "admin"]:
        role = "student"

    hashed_password = generate_password_hash(password)

    conn = get_db()
    cur = conn.cursor(dictionary=True)

    try:
        cur.execute(
            "INSERT INTO users (name, email, password, role) VALUES (%s, %s, %s, %s)",
            (name, email, hashed_password, role),
        )
        conn.commit()
    except mysql.connector.Error as err:
        conn.rollback()
        if err.errno == 1062:
            return jsonify({"message": "Email already registered"}), 400
        print("Register error:", err)
        return jsonify({"message": "DB error"}), 500
    finally:
        cur.close()
        conn.close()

    return jsonify({"message": "User registered successfully"})


@app.route("/auth/login", methods=["POST"])
def login():
    data = request.get_json()
    if not data:
        return jsonify({"message": "JSON body required"}), 400

    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"message": "Email and password are required"}), 400

    conn = get_db()
    cur = conn.cursor(dictionary=True)

    try:
        cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cur.fetchone()
    except mysql.connector.Error as err:
        print("Login error:", err)
        return jsonify({"message": "DB error"}), 500
    finally:
        cur.close()
        conn.close()

    if not user:
        return jsonify({"message": "User not found"}), 400

    if not check_password_hash(user["password"], password):
        return jsonify({"message": "Invalid password"}), 400

    token = create_token(user)

    return jsonify(
        {
            "message": "Login successful",
            "token": token,
            "user": {
                "id": user["id"],
                "name": user["name"],
                "email": user["email"],
                "role": user["role"],
            },
        }
    )


# ------- COMPLAINTS (STUDENT) --------

@app.route("/complaints", methods=["POST"])
@token_required
def create_complaint():
    user = request.user

    title = request.form.get("title")
    description = request.form.get("description")
    category = request.form.get("category")
    image_file = request.files.get("image")

    if not title or not description:
        return jsonify({"message": "Title and description are required"}), 400

    image_filename = None
    if image_file:
        filename = secure_filename(image_file.filename)
        if filename:
            unique_name = f"{int(datetime.datetime.utcnow().timestamp())}_{filename}"
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], unique_name)
            image_file.save(filepath)
            image_filename = unique_name

    conn = get_db()
    cur = conn.cursor(dictionary=True)

    try:
        cur.execute(
            "INSERT INTO complaints (user_id, title, description, category, image) "
            "VALUES (%s, %s, %s, %s, %s)",
            (user["id"], title, description, category, image_filename),
        )
        conn.commit()
        complaint_id = cur.lastrowid
    except mysql.connector.Error as err:
        conn.rollback()
        print("Create complaint error:", err)
        return jsonify({"message": "DB error"}), 500
    finally:
        cur.close()
        conn.close()

    return jsonify({"message": "Complaint created", "complaintId": complaint_id})


@app.route("/complaints/my", methods=["GET"])
@token_required
def get_my_complaints():
    user = request.user

    conn = get_db()
    cur = conn.cursor(dictionary=True)

    try:
        cur.execute(
            "SELECT * FROM complaints WHERE user_id = %s ORDER BY created_at DESC",
            (user["id"],),
        )
        rows = cur.fetchall()
    except mysql.connector.Error as err:
        print("Get my complaints error:", err)
        return jsonify({"message": "DB error"}), 500
    finally:
        cur.close()
        conn.close()

    return jsonify(rows)


@app.route("/uploads/<path:filename>")
def serve_image(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


# ------- COMMENTS (CHAT) --------

@app.route("/complaints/<int:complaint_id>/comments", methods=["POST"])
@token_required
def add_comment(complaint_id):
    user = request.user
    data = request.get_json()
    if not data:
        return jsonify({"message": "JSON body required"}), 400

    message = data.get("message")
    if not message:
        return jsonify({"message": "Message is required"}), 400

    conn = get_db()
    cur = conn.cursor(dictionary=True)

    try:
        cur.execute(
            "INSERT INTO comments (complaint_id, user_id, message) VALUES (%s, %s, %s)",
            (complaint_id, user["id"], message),
        )
        conn.commit()
    except mysql.connector.Error as err:
        conn.rollback()
        print("Add comment error:", err)
        return jsonify({"message": "DB error"}), 500
    finally:
        cur.close()
        conn.close()

    return jsonify({"message": "Comment added"})


@app.route("/complaints/<int:complaint_id>/comments", methods=["GET"])
@token_required
def get_comments(complaint_id):
    conn = get_db()
    cur = conn.cursor(dictionary=True)

    try:
        cur.execute(
            "SELECT c.id, c.message, c.created_at, "
            "u.name AS author_name, u.role AS author_role "
            "FROM comments c "
            "JOIN users u ON c.user_id = u.id "
            "WHERE c.complaint_id = %s "
            "ORDER BY c.created_at ASC",
            (complaint_id,),
        )
        rows = cur.fetchall()
    except mysql.connector.Error as err:
        print("Get comments error:", err)
        return jsonify({"message": "DB error"}), 500
    finally:
        cur.close()
        conn.close()

    return jsonify(rows)


# ------- ADMIN ROUTES --------

@app.route("/admin/complaints", methods=["GET"])
@admin_required
def get_all_complaints():
    conn = get_db()
    cur = conn.cursor(dictionary=True)

    try:
        cur.execute("SELECT * FROM complaints ORDER BY created_at DESC")
        rows = cur.fetchall()
    except mysql.connector.Error as err:
        print("Get all complaints error:", err)
        return jsonify({"message": "DB error"}), 500
    finally:
        cur.close()
        conn.close()

    return jsonify(rows)


@app.route("/admin/complaints/<int:complaint_id>/status", methods=["PUT"])
@admin_required
def update_status(complaint_id):
    data = request.get_json()
    if not data:
        return jsonify({"message": "JSON body required"}), 400

    status = data.get("status")
    allowed_status = ["Open", "In Progress", "Resolved"]
    if status not in allowed_status:
        return jsonify({"message": "Invalid status"}), 400

    conn = get_db()
    cur = conn.cursor(dictionary=True)

    try:
        cur.execute(
            "UPDATE complaints SET status = %s WHERE id = %s",
            (status, complaint_id),
        )
        conn.commit()
    except mysql.connector.Error as err:
        conn.rollback()
        print("Update status error:", err)
        return jsonify({"message": "DB error"}), 500
    finally:
        cur.close()
        conn.close()

    return jsonify({"message": "Status updated"})


@app.route("/admin/analytics/summary", methods=["GET"])
@admin_required
def analytics_summary():
    conn = get_db()
    cur = conn.cursor(dictionary=True)

    try:
        cur.execute(
            "SELECT status, COUNT(*) AS count FROM complaints GROUP BY status"
        )
        by_status = cur.fetchall()

        cur.execute(
            "SELECT IFNULL(category, 'Uncategorized') AS category, COUNT(*) AS count "
            "FROM complaints GROUP BY category"
        )
        by_category = cur.fetchall()
    except mysql.connector.Error as err:
        print("Analytics error:", err)
        return jsonify({"message": "DB error"}), 500
    finally:
        cur.close()
        conn.close()

    return jsonify({"byStatus": by_status, "byCategory": by_category})


# ================== MAIN ==================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
