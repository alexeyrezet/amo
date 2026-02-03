import os
import requests
import time
from flask import Flask, request

app = Flask(__name__)

# --- НАСТРОЙКИ ---
AMO_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImp0aSI6IjYyMTk0NDdhNWUyMTEyMGEzM2I2MDdmMzBhNDFlNzFmOWVlMzAyYTY1M2VlOGRmMmU4YWY0NTkwNjc1ODllNjQ1MjYxMGFhMDVjN2UxM2NlIn0.eyJhdWQiOiI5NWEyZmE3OS04M2RmLTRjMGMtOTlhZC1lYmQ4NDE5YjYwYjQiLCJqdGkiOiI2MjE5NDQ3YTVlMjExMjBhMzNiNjA3ZjMwYTQxZTcxZjllZTMwMmE2NTNlZThkZjJlOGFmNDU5MDY3NTg5ZTY0NTI2MTBhYTA1YzdlMTNjZSIsImlhdCI6MTc3MDA3NDQxMywibmJmIjoxNzcwMDc0NDEzLCJleHAiOjE3NzAxNjA4MTMsInN1YiI6IjEwNTg3ODY2IiwiZ3JhbnRfdHlwZSI6IiIsImFjY291bnRfaWQiOjMxNTI0OTU4LCJiYXNlX2RvbWFpbiI6ImFtb2NybS5ydSIsInZlcnNpb24iOjIsInNjb3BlcyI6WyJwdXNoX25vdGlmaWNhdGlvbnMiLCJmaWxlcyIsImNybSIsIm5vdGlmaWNhdGlvbnMiXSwiaGFzaF91dWlkIjoiNGIzMjYzY2ItZDc3MS00Njk1LTk1MjktMGMwZTY2M2M1NTA1IiwidXNlcl9mbGFncyI6MCwiYXBpX2RvbWFpbiI6ImFwaS1iLmFtb2NybS5ydSJ9.sE1i00tFMBecTtNRPTvsIAnDWoTWaFUIWh3WQIEY9F4Q_XrEIBdpBXq7OgiSpIISY_kWF1FqKv7a1LzlfzTFZjsM-3mSig8CdSTF7akcrDKI_5NhkUOiIir2XQJOkWKRRgvwvq5ohrShFAmHYqzNs54fm-3c_Py-AOsvPa-o78gGDPeahsW0dD8rxltr0ez9EuSWfw-6hItCi-NQJd8qOdWRmACMOW_1y4PtNWcPl-9qbOcS6ceNh2qu2Lm5pHkavIkpZZTgp6atRjNmwE2wRw8hkV6jFAZkxymU1IDmVk3jIsXYIcEZzqexKLugkrND9GQX0bcA9RKRyeaWDW2ACg"
SUBDOMAIN = "restartivanovo"
OPENAI_KEY = "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"

def get_ai_advice(text):
    print(f"🤖 Запрос к OpenAI для текста: {text[:30]}...")
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENAI_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "Ты эксперт сервисного центра по ремонту техники. Проанализируй сообщение клиента и дай менеджеру один очень короткий, профессиональный совет."},
            {"role": "user", "content": text}
        ],
        "max_tokens": 150,
        "temperature": 0.7
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=20)
        if response.status_code == 200:
            result = response.json()
            advice = result['choices'][0]['message']['content'].strip()
            print("✅ Ответ от ChatGPT получен")
            return advice
        else:
            print(f"❌ Ошибка OpenAI API: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"💥 Ошибка сети при запросе к OpenAI: {e}")
        return None

@app.route('/webhook', methods=['POST'])
def webhook():
    # Пробуем получить данные и из form-data, и из JSON
    data = request.form.to_dict() or request.get_json()
    if not data:
        return "No data", 200
        
    print(f"📞 Данные хука: {data}")

    # 1. Пробуем вытащить ID сделки
    lead_id = (data.get('message[add][0][entity_id]') or 
               data.get('leads[add][0][id]') or 
               data.get('talk[update][0][entity_id]'))

    # 2. Пробуем вытащить ТЕКСТ сообщения
    # Проверяем все возможные места, куда Амо может положить текст
    text = (data.get('message[add][0][text]') or 
            data.get('leads[add][0][name]') or 
            data.get('leads[update][0][name]'))

    if lead_id and text:
        print(f"🔎 Нашел сделку №{lead_id} и текст: {text}")
        advice = get_ai_advice(text)
        
        if advice:
            # Отправка примечания
            note_url = f"https://{SUBDOMAIN}.amocrm.ru/api/v4/leads/{lead_id}/notes"
            headers = {"Authorization": f"Bearer {AMO_TOKEN}", "Content-Type": "application/json"}
            note_data = [{"note_type": "common", "params": {"text": f"🤖 Совет GPT: {advice}"}}]
            res = requests.post(note_url, json=note_data, headers=headers)
            print(f"📤 Ответ amoCRM: {res.status_code}")
    else:
        # Если текста нет, мы не ругаемся, просто ждем следующий хук
        print("ℹ️ Получен технический хук без текста сообщения")

    return "OK", 200

if __name__ == "__main__":
    # Render сам назначит порт через переменную окружения PORT
    port = int(os.environ.get("PORT", 10000))

    app.run(host='0.0.0.0', port=port)
