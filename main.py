import os
import requests
import threading
import time
from flask import Flask, request
from google import genai

app = Flask(__name__)

# Настройки из окружения
GEMINI_KEY = os.environ.get("GEMINI_KEY")
AMO_TOKEN = os.environ.get("AMO_TOKEN")
SUBDOMAIN = "restartivanovo"

# Инициализация клиента (API 2026)
client_ai = genai.Client(api_key=GEMINI_KEY)

def ai_worker(lead_id, client_text):
    try:
        print(f"📡 Поток запущен. Работаю с Gemini 2.0...")
        
        # Модель 2.0 Flash сейчас самая стабильная и быстрая
        response = client_ai.models.generate_content(
            model='gemini-2.0-flash',
            contents=f"Ты эксперт. Дай краткий совет менеджеру: {client_text}"
        )

        if response and response.text:
            advice = response.text.strip()
            print(f"✅ ИИ ответил: {advice[:50]}...")
            
            # Отправка в AmoCRM
            url = f"https://{SUBDOMAIN}.amocrm.ru/api/v4/leads/{lead_id}/notes"
            headers = {"Authorization": f"Bearer {AMO_TOKEN}", "Content-Type": "application/json"}
            payload = [{"note_type": "common", "params": {"text": f"🤖 {advice}"}}]
            
            res = requests.post(url, json=payload, headers=headers, timeout=10)
            print(f"📤 AmoCRM статус: {res.status_code}")
            
    except Exception as e:
        print(f"💥 Ошибка в потоке: {e}")

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.form.to_dict()
    lead_id = data.get('message[add][0][entity_id]') or data.get('leads[update][0][id]')
    text = data.get('message[add][0][text]') or data.get('leads[update][0][name]')

    if lead_id and text:
        # Запускаем поток
        t = threading.Thread(target=ai_worker, args=(lead_id, text))
        t.start()
        # Даем крошечную паузу, чтобы поток успел стартовать до закрытия воркера
        time.sleep(0.1)

    return "OK", 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
