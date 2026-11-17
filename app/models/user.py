from app import db
from flask_login import UserMixin
from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(
        db.String(100),
        nullable=False
    )

    email = db.Column(
        db.String(150),
        unique=True,
        nullable=False,
        index=True
    )

    password_hash = db.Column(
        db.String(256),
        nullable=False
    )

    target_role = db.Column(
        db.String(100),
        nullable=True
    )

    # Latest resume analysis results
    resume_skills = db.Column(
        db.JSON,
        nullable=True
    )

    matched_skills = db.Column(
        db.JSON,
        nullable=True
    )

    missing_skills = db.Column(
        db.JSON,
        nullable=True
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(
            self.password_hash,
            password
        )

    def __repr__(self):
        return f"<User {self.email}>"