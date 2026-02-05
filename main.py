import os
import requests
from flask import Flask, request

app = Flask(__name__)

# Настройки
SUBDOMAIN = "restartivanovo"
# Эти ключи должны быть в Environment Variables на Render
AMO_TOKEN = os.environ.get("AMO_TOKEN")
GEMINI_KEY = os.environ.get("GEMINI_KEY")

def get_ai_advice(text):
    print(f"📡 Запрос к Gemini через прямой HTTP...")
    # Используем стабильную версию v1
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
    
    payload = {
        "contents": [{
            "parts": [{"text": f"Ты эксперт сервисного центра. Клиент пишет: {text}. Дай 1 очень короткий совет менеджеру."}]
        }]
    }
    
    try:
        response = requests.post(url, json=payload, timeout=20)
        print(f"🛰 Статус Google: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            advice = result['candidates'][0]['content']['parts'][0]['text']
            return advice
        else:
            print(f"❌ Ошибка Google: {response.text}")
            return None
    except Exception as e:
        print(f"💥 Ошибка запроса: {e}")
        return None

def send_to_amo(lead_id, advice):
    print(f"📤 Отправка в amoCRM для сделки {lead_id}...")
    url = f"https://{SUBDOMAIN}.amocrm.ru/api/v4/leads/{lead_id}/notes"
    headers = {
        "Authorization": f"Bearer {AMO_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = [{"note_type": "common", "params": {"text": f"🤖 Совет: {advice}"}}]
    
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=10)
        print(f"✅ amoCRM ответила: {res.status_code}")
    except Exception as e:
        print(f"💥 Ошибка amoCRM: {e}")

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.form.to_dict()
    # Извлекаем ID сделки и текст
    lead_id = data.get('message[add][0][entity_id]') or data.get('leads[update][0][id]')
    text = data.get('message[add][0][text]') or data.get('leads[update][0][name]')

    if lead_id and text:
        if "входящий" in text.lower():
            return "OK", 200

        # Получаем совет (синхронно, чтобы Render не закрыл соединение)
        advice = get_ai_advice(text)
        if advice:
            send_to_amo(lead_id, advice)
    
    return "OK", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
