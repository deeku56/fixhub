from flask import Flask, render_template, request, jsonify, redirect, url_for, send_from_directory
import os
import difflib
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from test_vision import extract_text, extract_name_and_dob

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = 'your_secret_key_here'

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///fixhub.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login_page"

# === MODELS ===
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

# === LOGIN MANAGER ===
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@login_manager.unauthorized_handler
def unauthorized():
    return redirect(url_for("login_page"))

# === ROUTES ===
@app.route("/")
@login_required
def index():
    return render_template("hub.html")

@app.route("/login")
def login_page():
    return render_template("login.html")

@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    email = data.get("email", "").strip()
    password = data.get("password", "").strip()

    if not email or not password:
        return jsonify({"message": "❌ Email and password are required."}), 400
    if "@" not in email or "." not in email:
        return jsonify({"message": "❌ Please enter a valid email address."}), 400
    if len(password) < 6:
        return jsonify({"message": "❌ Password must be at least 6 characters."}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({"message": "❌ Email already registered."}), 400

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

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return jsonify({"message": "✅ Logged out successfully."})

@app.route("/report-issue", methods=["POST"])
@login_required
def report_issue():
    data = request.get_json()
    if not data or not data.get("title") or not data.get("description") or not data.get("category"):
        return jsonify({"message": "❌ Please provide all required fields!"}), 400

    location_data = data.get("location") or f"{data.get('latitude')}, {data.get('longitude')}"
    new_issue = Issue(
        title=data["title"],
        description=data["description"],
        category=data["category"],
        location=location_data
    )
    db.session.add(new_issue)
    db.session.commit()
    return jsonify({"message": "✅ Issue submitted successfully!", "issue_id": new_issue.id})

@app.route("/get-issues", methods=["GET"])
@login_required
def get_issues():
    issues = Issue.query.all()
    upvoted_ids = {u.issue_id for u in Upvote.query.filter_by(user_id=current_user.id).all()}

    issue_list = [{
        "id": issue.id,
        "title": issue.title,
        "description": issue.description,
        "category": issue.category,
        "location": issue.location,
        "status": issue.status,
        "upvotes": issue.upvotes,
        "upvoted": issue.id in upvoted_ids
    } for issue in issues]

    return jsonify({"issues": issue_list})

@app.route("/upvote-issue", methods=["POST"])
@login_required
def upvote_issue():
    data = request.get_json()
    if not data or "issue_id" not in data:
        return jsonify({"message": "❌ Missing required data!"}), 400

    issue_id = int(data["issue_id"])
    issue = Issue.query.get(issue_id)
    if not issue:
        return jsonify({"message": "❌ Issue not found!"}), 404

    existing_upvote = Upvote.query.filter_by(user_id=current_user.id, issue_id=issue_id).first()
    if existing_upvote:
        return jsonify({"message": "⚠️ You have already upvoted this issue."}), 403

    issue.upvotes += 1
    db.session.add(Upvote(user_id=current_user.id, issue_id=issue_id))
    db.session.commit()
    return jsonify({"message": "✅ Upvote recorded!", "upvotes": issue.upvotes})

@app.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    if request.method == "POST":
        if request.is_json:
            # ✅ JavaScript fetch() request
            data = request.get_json()
            email = data.get("email", "").strip()
            new_password = data.get("new_password", "").strip()

            if not email or not new_password:
                return jsonify({"message": "❌ Email and password required."}), 400

            user = User.query.filter_by(email=email).first()
            if not user:
                return jsonify({"message": "❌ Email not found."}), 404

            user.set_password(new_password)
            db.session.commit()
            return jsonify({"message": "✅ Password reset successful!"})

        else:
            # 📝 Optional fallback (for regular POST form)
            email = request.form.get("email", "").strip()
            new_password = request.form.get("new_password", "").strip()
            if not email or not new_password:
                return render_template("pass.html", error="❌ Email and password required.")
            user = User.query.filter_by(email=email).first()
            if not user:
                return render_template("pass.html", error="❌ Email not found.")
            user.set_password(new_password)
            db.session.commit()
            return render_template("pass.html", success="✅ Password reset successful.")

    return render_template("pass.html")

@app.route("/verify-identity", methods=["POST"])
@login_required
def verify_identity():
    aadhar = request.files.get("aadhar")
    other_id = request.files.get("other_id")

    if not aadhar or not other_id:
        return jsonify({"status": "failed", "message": "❌ Please upload both Aadhaar and Proof images."}), 400

    uploads_folder = os.path.join(app.static_folder, "uploads")
    os.makedirs(uploads_folder, exist_ok=True)

    aadhar_path = os.path.join(uploads_folder, aadhar.filename)
    other_id_path = os.path.join(uploads_folder, other_id.filename)

    aadhar.save(aadhar_path)
    other_id.save(other_id_path)

    aadhaar_text = extract_text(aadhar_path)
    proof_text = extract_text(other_id_path)

    aadhaar_name, aadhaar_dob = extract_name_and_dob(aadhaar_text)
    proof_name, proof_dob = extract_name_and_dob(proof_text)

    name_similarity = difflib.SequenceMatcher(None, aadhaar_name.lower(), proof_name.lower()).ratio()
    names_match = name_similarity > 0.85
    dobs_match = aadhaar_dob.strip() == proof_dob.strip()

    if not names_match or not dobs_match:
        mismatch = []
        if not names_match:
            mismatch.append(f"Name mismatch ('{aadhaar_name}' vs '{proof_name}')")
        if not dobs_match:
            mismatch.append(f"DOB mismatch ('{aadhaar_dob}' vs '{proof_dob}')")
        return jsonify({"status": "failed", "message": f"❌ Identity verification failed: {', '.join(mismatch)}"})

    return jsonify({"status": "verified", "message": "✅ Verification successful!"})

@app.route("/static/<path:filename>")
def serve_static(filename):
    return send_from_directory(app.static_folder, filename)

# === Run App ===
if __name__ == "__main__":
    print("🚀 Starting FixHub server on http://127.0.0.1:5000")
    app.run(debug=True)
