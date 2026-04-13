import requests



API_URL = "https://ai.mindrayanimal.com/admin/api/workspace/default/knowledge/019d47f6-383b-7482-87c5-8a1007258bd5/tags"

AUTHORIZATION = "Bearer user-f86e223427899afdc5b711ba498e8bdc"
REQUEST_TIMEOUT = 60

def send_payload(api_url: str, authorization: str, payload) -> requests.Response:
    headers = {
        "Authorization": authorization,
        "Content-Type": "application/json"
    }
    response = requests.post(
        api_url,
        headers=headers,
        json=payload,
        timeout=REQUEST_TIMEOUT
    )
    return response
payload = [
    {"key": "型号", "value": "BC-75R Vet"},
    {"key": "型号", "value": "BC-60R Vet"},
    {"key": "型号", "value": "BC-5000Vet"},
    {"key": "型号", "value": "BC-20 Vet"},
    {"key": "型号", "value": "BC-30 Vet"},
    {"key": "型号", "value": "vetXpert I5"},
    {"key": "型号", "value": "vetXpert I3"},
    {"key": "型号", "value": "vetXpert C5"},
    {"key": "型号", "value": "vetXpert Cube"}
]

response = send_payload(API_URL, AUTHORIZATION, payload)



