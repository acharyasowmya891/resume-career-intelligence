from app import app, db
from sqlalchemy import inspect, text

with app.app_context():

    inspector = inspect(db.engine)

    columns = [
        column["name"]
        for column in inspector.get_columns("users")
    ]

    if "target_role" not in columns:

        with db.engine.begin() as connection:
            connection.execute(
                text(
                    "ALTER TABLE users "
                    "ADD COLUMN target_role VARCHAR(100)"
                )
            )

        print("Database updated successfully!")

    else:
        print("target_role column already exists.")
