from app.database import engine
from sqlalchemy import text

try:
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        print("Postgresql connected successfully, SELECT 1 returned:", result.scalar())

except Exception as e:
    print(f"connection failed: {e}")