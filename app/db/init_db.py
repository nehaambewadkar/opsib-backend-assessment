
from app.db.session import Base, engine
from app.db import models


def init_db() -> None:
    """Create database tables that do not already exist."""
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully.")


if __name__ == "__main__":
    init_db()
