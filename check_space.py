import requests

url = "https://huggingface.co/api/spaces/pibble123/Vishing-Detection-usingML-NLP"
response = requests.get(url)
if response.status_code == 200:
    data = response.json()
    print(f"Space Status: {data.get('runtime', {}).get('stage')}")
else:
    print(f"Failed to fetch status: {response.status_code}")
