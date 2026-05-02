import asyncio
from app.database import get_db, async_session
from app.routes.auth import register, UserRegister

async def test():
    async with async_session() as db:
        user_data = UserRegister(email="test3@example.com", password="password", name="Test User")
        try:
            res = await register(user_data=user_data, db=db)
            print("Success:", res)
        except Exception as e:
            print("Error:", repr(e))

asyncio.run(test())
