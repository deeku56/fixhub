from flask import Flask, render_template, request, jsonify, redirect, url_for, send_from_directory
import os
import difflib
import json
import re
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from google.cloud import vision
from google.oauth2 import service_account

# === Paths ===
basedir = os.path.abspath(os.path.dirname(__file__))
UPLOADS_DIR = os.path.join(basedir, "static", "uploads")
os.makedirs(UPLOADS_DIR, exist_ok=True)

# === Vision API Setup ===
def get_vision_client():
    try:
        if os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON"):
            credentials_json = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")
            credentials_dict = json.loads(credentials_json)
            credentials = service_account.Credentials.from_service_account_info(credentials_dict)
            print("✅ Google Vision API client initialized from JSON string")
            return vision.ImageAnnotatorClient(credentials=credentials)

        elif os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
            print("✅ Google Vision API client initialized from local file")
            return vision.ImageAnnotatorClient()

        else:
            raise ValueError("GOOGLE_APPLICATION_CREDENTIALS or _JSON is not set")

    except Exception as e:
        print("❌ Failed to initialize Vision API client:", e)
        return None

client = get_vision_client()

# === Flask App Setup ===
app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = os.environ.get("SECRET_KEY", "devkey")
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(basedir, 'instance', 'fixhub.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# === Extensions ===
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login_page"

# === Models ===
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Issue(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    location = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(50), default="Under Review")
    upvotes = db.Column(db.Integer, default=0)

class Upvote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    issue_id = db.Column(db.Integer, db.ForeignKey('issue.id'))

with app.app_context():
    db.create_all()

# === Vision Text Extraction Functions ===
def extract_text(image_path):
    if not client:
        return "❌ Vision API client not initialized"
    with open(image_path, "rb") as image_file:
        content = image_file.read()
    image = vision.Image(content=content)
    response = client.text_detection(image=image)
    texts = response.text_annotations
    return texts[0].description.strip() if texts else ""

def extract_name_and_dob(text):
    lines = text.splitlines()
    name = lines[0] if lines else "UNKNOWN"
    dob = next((line for line in lines if "199" in line or "200" in line), "UNKNOWN")
    return name.strip(), dob.strip()

# === User Management ===
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@login_manager.unauthorized_handler
def unauthorized():
    return redirect(url_for("login_page"))

# === Public Landing Page ===
@app.route("/")
def public_about():
    return render_template("hub.html")

# === Auth Pages ===
@app.route("/login")
def login_page():
    return render_template("login.html")

@app.route("/register")
def register_page():
    return render_template("register.html")

@app.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    if request.method == "POST":
        if request.is_json:
            data = request.get_json()
            email = data.get("email", "").strip()
            new_password = data.get("new_password", "").strip()
            if not email or not new_password:
                return jsonify({"message": "❌ Both fields required"}), 400
            user = User.query.filter_by(email=email).first()
            if not user:
                return jsonify({"message": "❌ Email not found"}), 404
            user.set_password(new_password)
            db.session.commit()
            return jsonify({"message": "✅ Password reset successful!"})
        else:
            email = request.form.get("email", "").strip()
            new_password = request.form.get("new_password", "").strip()
            user = User.query.filter_by(email=email).first()
            if not user:
                return render_template("pass.html", error="❌ Email not found.")
            user.set_password(new_password)
            db.session.commit()
            return render_template("pass.html", success="✅ Password reset successful.")
    return render_template("pass.html")

# === Main Features ===
@app.route("/features")
@login_required
def features():
    return render_template("features.html")

@app.route("/report")
@login_required
def report():
    return render_template("report.html")

@app.route("/track")
@login_required
def track():
    return render_template("track.html")

@app.route("/faq")
@login_required
def faq():
    return render_template("faq.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login_page"))

# === Auth APIs ===
@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    email = data.get("email", "").strip()
    password = data.get("password", "").strip()
    if not email or not password:
        return jsonify({"message": "❌ Email and password are required."}), 400
    if "@" not in email or "." not in email:
        return jsonify({"message": "❌ Invalid email address."}), 400
    if len(password) < 6:
        return jsonify({"message": "❌ Password too short."}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({"message": "❌ Email already exists."}), 400
    user = User(email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return jsonify({"message": "✅ Registered successfully!"})

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get("email", "").strip()
    password = data.get("password", "").strip()
    if not email or not password:
        return jsonify({"message": "❌ Email and password required."}), 400
    user = User.query.filter_by(email=email).first()
    if user and user.check_password(password):
        login_user(user)
        return jsonify({"message": "✅ Logged in!"})
    return jsonify({"message": "❌ Invalid credentials."}), 401

# === Identity Verification ===
@app.route("/verify-identity", methods=["POST"])
@login_required
def verify_identity():
    aadhar = request.files.get("aadhar")
    other_id = request.files.get("other_id")
    if not aadhar or not other_id:
        return jsonify({"status": "failed", "message": "❌ Upload both ID proofs."}), 400
    aadhar_path = os.path.join(UPLOADS_DIR, aadhar.filename)
    other_id_path = os.path.join(UPLOADS_DIR, other_id.filename)
    aadhar.save(aadhar_path)
    other_id.save(other_id_path)
    aadhar_text = extract_text(aadhar_path)
    proof_text = extract_text(other_id_path)
    name1, dob1 = extract_name_and_dob(aadhar_text)
    name2, dob2 = extract_name_and_dob(proof_text)
    name_match = difflib.SequenceMatcher(None, name1.lower(), name2.lower()).ratio() > 0.85
    dob_match = dob1 == dob2
    if not (name_match and dob_match):
        return jsonify({"status": "failed", "message": f"❌ Name or DOB mismatch ({name1} vs {name2})"}), 400
    return jsonify({"status": "verified", "message": "✅ Verification successful!"})

# === Issue APIs ===
@app.route("/report-issue", methods=["POST"])
@login_required
def report_issue():
    data = request.get_json()
    title = data.get("title", "").strip()
    desc = data.get("description", "").strip()
    category = data.get("category", "").strip()
    location = data.get("location") or f"{data.get('latitude')}, {data.get('longitude')}"
    if not title or not desc or not category:
        return jsonify({"message": "❌ All fields required."}), 400
    issue = Issue(title=title, description=desc, category=category, location=location)
    db.session.add(issue)
    db.session.commit()
    return jsonify({"message": "✅ Issue submitted.", "issue_id": issue.id})

@app.route("/get-issues", methods=["GET"])
@login_required
def get_issues():
    issues = Issue.query.all()
    upvoted = {u.issue_id for u in Upvote.query.filter_by(user_id=current_user.id)}
    issue_list = [{
        "id": i.id,
        "title": i.title,
        "description": i.description,
        "category": i.category,
        "location": i.location,
        "status": i.status,
        "upvotes": i.upvotes,
        "upvoted": i.id in upvoted
    } for i in issues]
    return jsonify({"issues": issue_list})

@app.route("/upvote-issue", methods=["POST"])
@login_required
def upvote_issue():
    data = request.get_json()
    issue_id = int(data.get("issue_id", 0))
    issue = Issue.query.get(issue_id)
    if not issue:
        return jsonify({"message": "❌ Issue not found."}), 404
    if Upvote.query.filter_by(user_id=current_user.id, issue_id=issue_id).first():
        return jsonify({"message": "⚠️ Already upvoted."}), 403
    db.session.add(Upvote(user_id=current_user.id, issue_id=issue_id))
    issue.upvotes += 1
    db.session.commit()
    return jsonify({"message": "✅ Upvote recorded!", "upvotes": issue.upvotes})

# === Admin Debug Route ===
@app.route("/reset-db")
@login_required
def reset_db():
    try:
        Upvote.query.delete()
        Issue.query.delete()
        db.session.commit()
        return "✅ All issues and upvotes reset!"
    except Exception as e:
        return f"❌ Reset failed: {e}"

# === Run App ===
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
