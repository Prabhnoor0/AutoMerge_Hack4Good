import requests

BASE_URL = "http://localhost:8000/api/auth"

def run_tests():
    print("Testing Registration...")
    res = requests.post(f"{BASE_URL}/register", json={
        "email": "test@example.com",
        "password": "password123",
        "name": "Test User"
    })
    
    if res.status_code == 200:
        print("Registration successful!")
    elif res.status_code == 400 and "already registered" in res.text:
        print("User already registered. Proceeding...")
    else:
        print(f"Registration failed: {res.text}")
        return

    print("Testing Login...")
    session = requests.Session()
    res = session.post(f"{BASE_URL}/login", json={
        "email": "test@example.com",
        "password": "password123"
    })
    
    if res.status_code == 200:
        print("Login successful! Cookies:", session.cookies.get_dict())
    else:
        print(f"Login failed: {res.text}")
        return

    print("Testing /me...")
    res = session.get(f"{BASE_URL}/me")
    if res.status_code == 200:
        print("Me successful! User:", res.json())
    else:
        print(f"Me failed: {res.text}")

    print("Testing Logout...")
    res = session.post(f"{BASE_URL}/logout")
    if res.status_code == 200:
        print("Logout successful! Cookies:", session.cookies.get_dict())
    else:
        print(f"Logout failed: {res.text}")

run_tests()
