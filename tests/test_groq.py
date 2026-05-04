import requests, time, random, string

# Create a fresh user
rnd = ''.join(random.choices(string.ascii_lowercase, k=6))
username = f'groqtest_{rnd}'
password = 'GroqTest@123456'

r = requests.post('http://localhost:8000/api/auth/register', json={
    'username': username,
    'password': password,
})
print(f"Register: {r.status_code}")
token = r.json().get('token', '')

if not token:
    print("Registration failed, trying login...")
    r = requests.post('http://localhost:8000/api/auth/login', json={
        'username': 'admin',
        'password': 'Admin@12345678',
    })
    token = r.json().get('token', '')

print(f"Token acquired: {'yes' if token else 'no'}")
print()

# Test 1: Vishing transcript
print("=" * 50)
print("TEST 1: Vishing Transcript")
print("=" * 50)
t0 = time.time()
res = requests.post('http://localhost:8000/api/analyze', json={
    'transcript': 'This is the bank security department. Your account has been suspended due to suspicious unauthorized activity. You must verify your details and OTP immediately or legal action will be taken. Do not tell anyone about this call. Press 1 now.',
    'model_choice': 'SVM',
    'input_mode': 'text',
}, headers={'Authorization': f'Bearer {token}'})
elapsed = time.time() - t0

data = res.json()
print(f"Status: {res.status_code}")
print(f"Verdict: {data.get('verdict')}")
print(f"Source: {data.get('source')}")
print(f"Confidence: {data.get('confidence')}")
print(f"AI Status: {data.get('ai_status')}")
print(f"Scam Type: {data.get('scam_type')}")
print(f"Tactics: {data.get('tactics')}")
print(f"Explanation: {str(data.get('explanation',''))[:300]}")
print(f"Action Steps: {data.get('action_steps')}")
print(f"Time: {elapsed:.2f}s")
print()

# Test 2: Safe transcript
print("=" * 50)
print("TEST 2: Safe Transcript")
print("=" * 50)
t0 = time.time()
res2 = requests.post('http://localhost:8000/api/analyze', json={
    'transcript': 'Hello, this is a courtesy call from the pharmacy. Your prescription is ready for pickup. Please bring your MyKad when you collect it. Our opening hours are 9am to 6pm. Have a great day.',
    'model_choice': 'SVM',
    'input_mode': 'text',
}, headers={'Authorization': f'Bearer {token}'})
elapsed2 = time.time() - t0

data2 = res2.json()
print(f"Status: {res2.status_code}")
print(f"Verdict: {data2.get('verdict')}")
print(f"Source: {data2.get('source')}")
print(f"Confidence: {data2.get('confidence')}")
print(f"AI Status: {data2.get('ai_status')}")
print(f"Time: {elapsed2:.2f}s")
