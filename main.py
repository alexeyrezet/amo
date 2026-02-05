import os
import threading
import requests
from flask import Flask, request
from google import genai  # Используем только новый пакет

app = Flask(__name__)

# --- Конфигурация ---
GEMINI_KEY = os.environ.get("GEMINI_KEY")
AMO_TOKEN = os.environ.get("AMO_TOKEN")
SUBDOMAIN = "restartivanovo"

# Инициализация клиента Gemini по новому стандарту
client = genai.Client(api_key=GEMINI_KEY)

def ai_worker(lead_id, client_text):
    try:
        print(f"🚀 Запуск Gemini 3 Flash Preview для сделки {lead_id}...")
        
        # Модель берем СТРОГО из твоего списка доступности
        response = client.models.generate_content(
            model="gemini-3-flash-preview", 
            contents=f"Ты эксперт сервисного центра. Клиент пишет: {client_text}. Дай ОДИН очень короткий совет менеджеру."
        )
        
        if response and response.text:
            advice = response.text.strip()
            print(f"✅ Gemini 3 ответила: {advice[:50]}...")
            
            # Отправка в amoCRM
            amo_url = f"https://{SUBDOMAIN}.amocrm.ru/api/v4/leads/{lead_id}/notes"
            headers = {
                "Authorization": f"Bearer {AMO_TOKEN}",
                "Content-Type": "application/json"
            }
            payload = [{"note_type": "common", "params": {"text": f"🤖 ИИ: {advice}"}}]
            
            res = requests.post(amo_url, json=payload, headers=headers, timeout=10)
            print(f"📤 Статус amoCRM: {res.status_code}")
            
    except Exception as e:
        print(f"❌ Ошибка в работе ИИ: {e}")

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.form.to_dict()
    
    # Логика извлечения ID и текста
    lead_id = data.get('message[add][0][entity_id]') or data.get('leads[update][0][id]')
    text = data.get('message[add][0][text]') or data.get('leads[update][0][name]')

    if lead_id and text:
        # Важно: запускаем в потоке, чтобы Render не разорвал соединение
        threading.Thread(target=ai_worker, args=(lead_id, text)).start()
    
    return "OK", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
