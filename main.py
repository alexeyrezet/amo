import os
import threading
from flask import Flask, request
import requests
from google import genai

app = Flask(__name__)

# Настройки (берем из переменных окружения Render)
GEMINI_KEY = os.environ.get("GEMINI_KEY")
AMO_TOKEN = os.environ.get("AMO_TOKEN")
SUBDOMAIN = "restartivanovo"

# Инициализация клиента Gemini 3
# Библиотека сама определит нужные эндпоинты v1alpha/v1beta
client = genai.Client(api_key=GEMINI_KEY)

def ai_worker(lead_id, client_text):
    try:
        print(f"⚡ Запрос к Gemini 3 Flash по сделке {lead_id}...")
        
        # Вызов модели Gemini 3
        response = client.models.generate_content(
            model="gemini-3-flash", 
            contents=f"Ты эксперт. Клиент пишет: {client_text}. Дай 1 очень короткий совет менеджеру."
        )
        
        if response and response.text:
            advice = response.text.strip()
            print(f"✨ Gemini 3 ответила: {advice[:50]}...")
            
            # Отправка в amoCRM
            url = f"https://{SUBDOMAIN}.amocrm.ru/api/v4/leads/{lead_id}/notes"
            headers = {
                "Authorization": f"Bearer {AMO_TOKEN}",
                "Content-Type": "application/json"
            }
            payload = [{"note_type": "common", "params": {"text": f"🤖 Gemini 3: {advice}"}}]
            
            res = requests.post(url, json=payload, headers=headers, timeout=10)
            print(f"📤 amoCRM статус: {res.status_code}")
        else:
            print("⚠️ Модель вернула пустой ответ.")

    except Exception as e:
        # Если модель gemini-3-flash еще не доступна в твоем регионе, 
        # библиотека выдаст ошибку здесь.
        print(f"❌ Ошибка Gemini 3: {e}")

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.form.to_dict()
    lead_id = data.get('message[add][0][entity_id]') or data.get('leads[update][0][id]')
    text = data.get('message[add][0][text]') or data.get('leads[update][0][name]')

    if lead_id and text:
        # Фоновый запуск, чтобы не вешать вебхук
        threading.Thread(target=ai_worker, args=(lead_id, text)).start()
    
    return "OK", 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
