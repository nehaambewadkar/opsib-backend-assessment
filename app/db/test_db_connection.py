
from sqlalchemy import text

from app.db.session import engine


try:
    with engine.connect() as connection:
        result = connection.execute(text("SELECT version()"))
        print("Database connection successful!")
        print(result.scalar())
except Exception as error:
    print("Database connection failed.")
    print(type(error).__name__, str(error))
finally:
    engine.dispose()
