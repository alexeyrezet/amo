import os
import requests
import threading
from flask import Flask, request
from google import genai

app = Flask(__name__)

# Настройки
SUBDOMAIN = "restartivanovo"
CLIENT_ID = os.environ.get("CLIENT_ID")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET")
GEMINI_KEY = os.environ.get("GEMINI_KEY")

# Эти переменные будут обновляться в памяти
current_access = os.environ.get("AMO_TOKEN")
current_refresh = os.environ.get("REFRESH_TOKEN")

# Инициализация Gemini 3
client_ai = genai.Client(api_key=GEMINI_KEY)

def refresh_tokens():
    """Автоматически обновляет Access Token через Refresh Token"""
    global current_access, current_refresh
    print("🔄 Обновляю токены amoCRM...")
    url = f"https://{SUBDOMAIN}.amocrm.ru/oauth2/access_token"
    payload = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "refresh_token",
        "refresh_token": current_refresh,
        "redirect_uri": "https://amo-djr3.onrender.com"
    }
    try:
        res = requests.post(url, json=payload, timeout=10)
        if res.status_code == 200:
            data = res.json()
            current_access = data['access_token']
            current_refresh = data['refresh_token']
            print("✅ Токены обновлены!")
            return True
    except Exception as e:
        print(f"💥 Ошибка рефреша: {e}")
    return False

def send_to_amo(lead_id, text, retry=True):
    """Отправляет совет в amoCRM, при 401 — обновляет токен"""
    global current_access
    url = f"https://{SUBDOMAIN}.amocrm.ru/api/v4/leads/{lead_id}/notes"
    headers = {"Authorization": f"Bearer {current_access}"}
    payload = [{"note_type": "common", "params": {"text": f"🤖 Gemini 3: {text}"}}]
    
    res = requests.post(url, json=payload, headers=headers)
    
    if res.status_code == 401 and retry:
        if refresh_tokens():
            return send_to_amo(lead_id, text, retry=False)
    
    print(f"📤 Результат amoCRM: {res.status_code}")

def ai_worker(lead_id, client_text):
    """Логика ИИ в фоновом потоке"""
    try:
        # Используем модель Gemini 3 Flash
        response = client_ai.models.generate_content(
            model="gemini-3-flash",
            contents=f"Ты эксперт сервисного центра. Клиент пишет: '{client_text}'. Дай менеджеру 1 очень короткий совет."
        )
        if response.text:
            send_to_amo(lead_id, response.text)
    except Exception as e:
        print(f"❌ Ошибка Gemini: {e}")

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.form.to_dict()
    lead_id = data.get('message[add][0][entity_id]') or data.get('leads[update][0][id]')
    text = data.get('message[add][0][text]') or data.get('leads[update][0][name]')

    if lead_id and text:
        if "входящий" in text.lower() and "успешный" in text.lower():
            return "OK", 200
        
        # Запуск ИИ в фоне, чтобы сразу ответить amoCRM "OK"
        threading.Thread(target=ai_worker, args=(lead_id, text)).start()

    return "OK", 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))