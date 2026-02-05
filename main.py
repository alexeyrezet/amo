import os
import requests
import time
from flask import Flask, request

app = Flask(__name__)

# --- НАСТРОЙКИ ---
AMO_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImp0aSI6IjYyMTk0NDdhNWUyMTEyMGEzM2I2MDdmMzBhNDFlNzFmOWVlMzAyYTY1M2VlOGRmMmU4YWY0NTkwNjc1ODllNjQ1MjYxMGFhMDVjN2UxM2NlIn0.eyJhdWQiOiI5NWEyZmE3OS04M2RmLTRjMGMtOTlhZC1lYmQ4NDE5YjYwYjQiLCJqdGkiOiI2MjE5NDQ3YTVlMjExMjBhMzNiNjA3ZjMwYTQxZTcxZjllZTMwMmE2NTNlZThkZjJlOGFmNDU5MDY3NTg5ZTY0NTI2MTBhYTA1YzdlMTNjZSIsImlhdCI6MTc3MDA3NDQxMywibmJmIjoxNzcwMDc0NDEzLCJleHAiOjE3NzAxNjA4MTMsInN1YiI6IjEwNTg3ODY2IiwiZ3JhbnRfdHlwZSI6IiIsImFjY291bnRfaWQiOjMxNTI0OTU4LCJiYXNlX2RvbWFpbiI6ImFtb2NybS5ydSIsInZlcnNpb24iOjIsInNjb3BlcyI6WyJwdXNoX25vdGlmaWNhdGlvbnMiLCJmaWxlcyIsImNybSIsIm5vdGlmaWNhdGlvbnMiXSwiaGFzaF91dWlkIjoiNGIzMjYzY2ItZDc3MS00Njk1LTk1MjktMGMwZTY2M2M1NTA1IiwidXNlcl9mbGFncyI6MCwiYXBpX2RvbWFpbiI6ImFwaS1iLmFtb2NybS5ydSJ9.sE1i00tFMBecTtNRPTvsIAnDWoTWaFUIWh3WQIEY9F4Q_XrEIBdpBXq7OgiSpIISY_kWF1FqKv7a1LzlfzTFZjsM-3mSig8CdSTF7akcrDKI_5NhkUOiIir2XQJOkWKRRgvwvq5ohrShFAmHYqzNs54fm-3c_Py-AOsvPa-o78gGDPeahsW0dD8rxltr0ez9EuSWfw-6hItCi-NQJd8qOdWRmACMOW_1y4PtNWcPl-9qbOcS6ceNh2qu2Lm5pHkavIkpZZTgp6atRjNmwE2wRw8hkV6jFAZkxymU1IDmVk3jIsXYIcEZzqexKLugkrND9GQX0bcA9RKRyeaWDW2ACg"
SUBDOMAIN = "restartivanovo"
GEMINI_KEY = "AIzaSyAKah9F8kBpgTb6YaWbhz2jxQisdDnFqvI" # Тот, за который теперь платишь

def get_ai_advice(text):
    if not text or len(text.strip()) < 2:
        return None

    print(f"🤖 Запрос к Gemini Flash: {text[:50]}...")
    # Используем стабильный эндпоинт v1beta для Gemini 2.0 Flash
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_KEY}"
    
    payload = {
        "contents": [{
            "parts": [{"text": f"Ты эксперт сервисного центра. Дай 1 очень короткий совет менеджеру, как ответить клиенту: {text}"}]
        }],
        "generationConfig": {
            "maxOutputTokens": 100,
            "temperature": 0.7
        }
    }

    try:
        response = requests.post(url, json=payload, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            # Извлекаем текст ответа
            advice = data['candidates'][0]['content']['parts'][0]['text']
            print("✅ Gemini успешно сгенерировала ответ")
            return advice
        else:
            print(f"❌ Ошибка Gemini API: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"💥 Сбой при запросе к ИИ: {e}")
        return None

@app.route('/webhook', methods=['POST'])
def webhook():
    # amoCRM шлет данные в формате x-www-form-urlencoded
    data = request.form.to_dict()
    
    # Пытаемся найти ID сделки в разных полях хука
    lead_id = (data.get('message[add][0][entity_id]') or 
               data.get('leads[add][0][id]') or 
               data.get('leads[update][0][id]') or
               data.get('talk[update][0][entity_id]'))

    # Пытаемся найти ТЕКСТ сообщения
    text = (data.get('message[add][0][text]') or 
            data.get('leads[add][0][name]') or
            data.get('leads[update][0][name]'))

    if lead_id and text:
        # Игнорируем технические названия входящих сделок
        if "входящий" in text.lower() and "успешный" in text.lower():
            print(f"ℹ️ Пропускаем технический хук для сделки {lead_id}")
            return "OK", 200

        print(f"🔎 Обработка сообщения для сделки №{lead_id}: {text[:30]}...")
        advice = get_ai_advice(text)
        
        if advice:
            # Отправка примечания в amoCRM
            url = f"https://{SUBDOMAIN}.amocrm.ru/api/v4/leads/{lead_id}/notes"
            headers = {
                "Authorization": f"Bearer {AMO_TOKEN}",
                "Content-Type": "application/json"
            }
            note_data = [{"note_type": "common", "params": {"text": f"🤖 Gemini Flash: {advice}"}}]
            
            res = requests.post(url, json=note_data, headers=headers)
            print(f"📤 Ответ amoCRM: {res.status_code}")
    
    return "OK", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)