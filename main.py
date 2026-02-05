import os
import requests
from flask import Flask, request
from google import genai

app = Flask(__name__)

# --- Конфигурация ---
GEMINI_KEY = os.environ.get("GEMINI_KEY")
AMO_TOKEN = os.environ.get("AMO_TOKEN")
SUBDOMAIN = "restartivanovo"

# Инициализация клиента
client = genai.Client(api_key=GEMINI_KEY)

def get_ai_advice(client_text):
    """Синхронный запрос к Gemini"""
    try:
        print(f"📡 Запрос к Gemini 3 Flash Preview...")
        response = client.models.generate_content(
            model="gemini-3-flash-preview", 
            contents=f"Ты эксперт сервисного центра. Клиент пишет: {client_text}. Дай 1 очень короткий совет менеджеру."
        )
        if response and response.text:
            return response.text.strip()
    except Exception as e:
        print(f"❌ Ошибка Gemini: {e}")
    return None

def send_to_amo(lead_id, advice):
    """Отправка в amoCRM"""
    url = f"https://{SUBDOMAIN}.amocrm.ru/api/v4/leads/{lead_id}/notes"
    headers = {
        "Authorization": f"Bearer {AMO_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = [{"note_type": "common", "params": {"text": f"🤖 ИИ: {advice}"}}]
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=10)
        print(f"📤 amoCRM статус: {res.status_code}")
    except Exception as e:
        print(f"💥 Ошибка amoCRM: {e}")

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.form.to_dict()
    
    # Извлечение данных
    lead_id = data.get('message[add][0][entity_id]') or data.get('leads[update][0][id]')
    text = data.get('message[add][0][text]') or data.get('leads[update][0][name]')

    if lead_id and text:
        # ВАЖНО: Делаем всё последовательно, не отпускаем вебхук пока не закончим
        advice = get_ai_advice(text)
        if advice:
            send_to_amo(lead_id, advice)
    
    # Только теперь отвечаем amoCRM
    return "OK", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
