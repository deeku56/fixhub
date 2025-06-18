from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

# Initialize DB
db = SQLAlchemy()

# User Table
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

# Civic Issue Table
class Issue(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.String(250))
    location = db.Column(db.String(200))
    category = db.Column(db.String(50))
    status = db.Column(db.String(50), default="Under Review")
    upvotes = db.Column(db.Integer, default=0)
    lat = db.Column(db.String(50))
    lng = db.Column(db.String(50))

# Upvotes Table
class Upvote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    issue_id = db.Column(db.Integer)
