import os
import requests
from flask import Flask, request

app = Flask(__name__)

# Данные подставляем свои
AMO_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImp0aSI6IjYyMTk0NDdhNWUyMTEyMGEzM2I2MDdmMzBhNDFlNzFmOWVlMzAyYTY1M2VlOGRmMmU4YWY0NTkwNjc1ODllNjQ1MjYxMGFhMDVjN2UxM2NlIn0.eyJhdWQiOiI5NWEyZmE3OS04M2RmLTRjMGMtOTlhZC1lYmQ4NDE5YjYwYjQiLCJqdGkiOiI2MjE5NDQ3YTVlMjExMjBhMzNiNjA3ZjMwYTQxZTcxZjllZTMwMmE2NTNlZThkZjJlOGFmNDU5MDY3NTg5ZTY0NTI2MTBhYTA1YzdlMTNjZSIsImlhdCI6MTc3MDA3NDQxMywibmJmIjoxNzcwMDc0NDEzLCJleHAiOjE3NzAxNjA4MTMsInN1YiI6IjEwNTg3ODY2IiwiZ3JhbnRfdHlwZSI6IiIsImFjY291bnRfaWQiOjMxNTI0OTU4LCJiYXNlX2RvbWFpbiI6ImFtb2NybS5ydSIsInZlcnNpb24iOjIsInNjb3BlcyI6WyJwdXNoX25vdGlmaWNhdGlvbnMiLCJmaWxlcyIsImNybSIsIm5vdGlmaWNhdGlvbnMiXSwiaGFzaF91dWlkIjoiNGIzMjYzY2ItZDc3MS00Njk1LTk1MjktMGMwZTY2M2M1NTA1IiwidXNlcl9mbGFncyI6MCwiYXBpX2RvbWFpbiI6ImFwaS1iLmFtb2NybS5ydSJ9.sE1i00tFMBecTtNRPTvsIAnDWoTWaFUIWh3WQIEY9F4Q_XrEIBdpBXq7OgiSpIISY_kWF1FqKv7a1LzlfzTFZjsM-3mSig8CdSTF7akcrDKI_5NhkUOiIir2XQJOkWKRRgvwvq5ohrShFAmHYqzNs54fm-3c_Py-AOsvPa-o78gGDPeahsW0dD8rxltr0ez9EuSWfw-6hItCi-NQJd8qOdWRmACMOW_1y4PtNWcPl-9qbOcS6ceNh2qu2Lm5pHkavIkpZZTgp6atRjNmwE2wRw8hkV6jFAZkxymU1IDmVk3jIsXYIcEZzqexKLugkrND9GQX0bcA9RKRyeaWDW2ACg"
SUBDOMAIN = "restartivanovo"
GEMINI_KEY = "AIzaSyAmJnFM3TKos72cdKP_1t1Q9nuzCXT7b2U"

def get_ai_advice(text):
    # Оставляем Gemini 2.0 Flash
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_KEY}"
    try:
        response = requests.post(url, json={
            "contents": [{"parts": [{"text": f"Ты эксперт. Дай краткий совет менеджеру: {text}"}]}]
        }, timeout=10)
        if response.status_code == 200:
            return response.json()['candidates'][0]['content']['parts'][0]['text']
        return f"Ошибка ИИ ({response.status_code})"
    except Exception as e:
        return f"Ошибка сети: {e}"

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.form.to_dict()
    lead_id = data.get('message[add][0][entity_id]')
    msg_text = data.get('message[add][0][text]')

    if lead_id and msg_text:
        advice = get_ai_advice(msg_text)
        note_url = f"https://{SUBDOMAIN}.amocrm.ru/api/v4/leads/{lead_id}/notes"
        headers = {"Authorization": f"Bearer {AMO_TOKEN}"}
        requests.post(note_url, json=[{"note_type": "common", "params": {"text": f"🤖 Gemini 2.0: {advice}"}}], headers=headers)

    return "OK", 200

if __name__ == "__main__":
    # Render сам назначит порт через переменную окружения
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)