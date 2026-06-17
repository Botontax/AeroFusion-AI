from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # 將 SimBrief ID 作為唯一登入憑證
    simbrief_id = db.Column(db.String(120), unique=True, nullable=False)