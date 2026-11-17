from app import app, db
from app.models.user import User

with app.app_context():
    db.create_all()
    print("Database initialized successfully!")
    print("User table is ready.")
