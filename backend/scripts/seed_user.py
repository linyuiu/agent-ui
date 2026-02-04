import os

from app import config  # noqa: F401
from app import models, security
from app.db import Base, SessionLocal, engine


def main() -> None:
    Base.metadata.create_all(bind=engine)

    email = os.getenv("SEED_EMAIL", "demo@example.com")
    password = os.getenv("SEED_PASSWORD", "Demo1234")

    db = SessionLocal()
    try:
        existing = (
            db.query(models.User)
            .filter(models.User.email == email)
            .first()
        )
        if existing:
            print(f"User already exists: {email}")
            return

        user = models.User(email=email, password_hash=security.hash_password(password))
        db.add(user)
        db.commit()
        print(f"Created user: {email}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
