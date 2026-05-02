import asyncio
from sqlalchemy import text
from app.database import engine, Base
from app.models import User

async def migrate():
    async with engine.begin() as conn:
        # Create users table
        await conn.run_sync(Base.metadata.create_all)
        
        # Add user_id to jobs
        try:
            await conn.execute(text("ALTER TABLE jobs ADD COLUMN user_id VARCHAR(12) REFERENCES users(id)"))
        except Exception as e:
            if "duplicate column name" not in str(e).lower():
                print(f"Jobs alter error: {e}")
                
        # Add user_id to classroom_reports
        try:
            await conn.execute(text("ALTER TABLE classroom_reports ADD COLUMN user_id VARCHAR(12) REFERENCES users(id)"))
        except Exception as e:
            if "duplicate column name" not in str(e).lower():
                print(f"Classroom reports alter error: {e}")
                
    print("Migration done")

asyncio.run(migrate())
