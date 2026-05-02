import asyncio
from app.services.llm_service import analyze_code_for_logic_bugs

code = """
def get_discounted_price(price, discount):
    final_price = price - (price * discount / 100)
    return final_price

price = "1000"  # galat type (string hona nahi chahiye)
discount = 10
print(get_discounted_price(price, discount))
"""

async def run():
    res = await analyze_code_for_logic_bugs(code, "python")
    print(res)

asyncio.run(run())
