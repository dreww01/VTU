import requests
import json

url = "https://coalless-maurine-superaccurate.ngrok-free.dev/transactions/webhook/vtpass/"

data = {
    "request_id": "REF_1765238128752",
    "status": "failed",  # This will change it to failed
}

response = requests.post(url, json=data)
print(f"Status Code: {response.status_code}")
print(f"Response: {response.json()}")