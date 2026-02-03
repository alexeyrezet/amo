import os
import requests
import time
from flask import Flask, request

app = Flask(__name__)

# --- НАСТРОЙКИ ---
AMO_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImp0aSI6IjYyMTk0NDdhNWUyMTEyMGEzM2I2MDdmMzBhNDFlNzFmOWVlMzAyYTY1M2VlOGRmMmU4YWY0NTkwNjc1ODllNjQ1MjYxMGFhMDVjN2UxM2NlIn0.eyJhdWQiOiI5NWEyZmE3OS04M2RmLTRjMGMtOTlhZC1lYmQ4NDE5YjYwYjQiLCJqdGkiOiI2MjE5NDQ3YTVlMjExMjBhMzNiNjA3ZjMwYTQxZTcxZjllZTMwMmE2NTNlZThkZjJlOGFmNDU5MDY3NTg5ZTY0NTI2MTBhYTA1YzdlMTNjZSIsImlhdCI6MTc3MDA3NDQxMywibmJmIjoxNzcwMDc0NDEzLCJleHAiOjE3NzAxNjA4MTMsInN1YiI6IjEwNTg3ODY2IiwiZ3JhbnRfdHlwZSI6IiIsImFjY291bnRfaWQiOjMxNTI0OTU4LCJiYXNlX2RvbWFpbiI6ImFtb2NybS5ydSIsInZlcnNpb24iOjIsInNjb3BlcyI6WyJwdXNoX25vdGlmaWNhdGlvbnMiLCJmaWxlcyIsImNybSIsIm5vdGlmaWNhdGlvbnMiXSwiaGFzaF91dWlkIjoiNGIzMjYzY2ItZDc3MS00Njk1LTk1MjktMGMwZTY2M2M1NTA1IiwidXNlcl9mbGFncyI6MCwiYXBpX2RvbWFpbiI6ImFwaS1iLmFtb2NybS5ydSJ9.sE1i00tFMBecTtNRPTvsIAnDWoTWaFUIWh3WQIEY9F4Q_XrEIBdpBXq7OgiSpIISY_kWF1FqKv7a1LzlfzTFZjsM-3mSig8CdSTF7akcrDKI_5NhkUOiIir2XQJOkWKRRgvwvq5ohrShFAmHYqzNs54fm-3c_Py-AOsvPa-o78gGDPeahsW0dD8rxltr0ez9EuSWfw-6hItCi-NQJd8qOdWRmACMOW_1y4PtNWcPl-9qbOcS6ceNh2qu2Lm5pHkavIkpZZTgp6atRjNmwE2wRw8hkV6jFAZkxymU1IDmVk3jIsXYIcEZzqexKLugkrND9GQX0bcA9RKRyeaWDW2ACg"
SUBDOMAIN = "restartivanovo"
GEMINI_KEY = "AIzaSyBzqaGaeHT8kSkLLI4OQaYuKFXKsLNQCIk"

def get_ai_advice(text):
    print(f"🤖 Отправляем текст в Gemini: {text[:50]}...")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_KEY}"
    
    try:
        # Увеличили таймаут до 30 секунд
        response = requests.post(url, json={
            "contents": [{"parts": [{"text": f"Ты эксперт. Дай краткий совет менеджеру: {text}"}]}]
        }, timeout=30)
        
        if response.status_code == 200:
            advice = response.json()['candidates'][0]['content']['parts'][0]['text']
            print("✅ Gemini успешно сгенерировал совет")
            return advice
        else:
            print(f"❌ Ошибка Gemini: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"💥 Ошибка при запросе к ИИ: {e}")
        return None

@app.route('/webhook', methods=['POST'])
def webhook():
    # 1. Получаем данные
    data = request.form.to_dict()
    print(f"📞 Получен вебхук! Данные: {data}") # Увидим, что прислала Амо

    # 2. Извлекаем ID сделки и текст
    # В разных типах хуков амо ключи могут отличаться, проверяем основные
    lead_id = data.get('leads[add][0][id]') or data.get('message[add][0][entity_id]')
    text = data.get('leads[add][0][name]') or data.get('message[add][0][text]')

    if lead_id and text:
        print(f"🔎 Работаем со сделкой: {lead_id}")
        advice = get_ai_advice(text)
        
        if advice:
            # 3. Отправляем в amoCRM
            note_url = f"https://{SUBDOMAIN}.amocrm.ru/api/v4/leads/{lead_id}/notes"
            headers = {"Authorization": f"Bearer {AMO_TOKEN}", "Content-Type": "application/json"}
            note_data = [{"note_type": "common", "params": {"text": f"🤖 Gemini 2.0: {advice}"}}]
            
            res = requests.post(note_url, json=note_data, headers=headers)
            print(f"📤 Ответ amoCRM при создании заметки: {res.status_code}")
            if res.status_code != 200:
                print(f"⚠️ Текст ошибки Амо: {res.text}")
    else:
        print("❓ Вебхук пришел, но ID сделки или текст не найдены в данных")

    return "OK", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)