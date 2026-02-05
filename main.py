import os
import requests
import threading
from flask import Flask, request
from google import genai
from google.genai import Client

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
    # Добавим принт сюда, чтобы видеть попытку отправки
    print(f"📤 Попытка отправить примечание в amoCRM для {lead_id}...")
    # ... твой код отправки ...

def ai_worker(lead_id, client_text):
    print(f"📡 Подготовка запроса для сделки {lead_id}...")
    model_id = "gemini-1.5-flash"
    
    try:
        # Устанавливаем ограничение по времени, чтобы не висело вечно
        print(f"🚀 Отправка данных в Google AI ({model_id})...")
        
        response = client_ai.models.generate_content(
            model=model_id,
            contents=f"Ты помощник в CRM. Клиент пишет: {client_text}. Дай совет в 1 предложении."
        )
        
        print(f"🛰 Ответ от Google получен!")
        
        if response and response.text:
            print(f"✅ Текст ответа: {response.text[:50]}...")
            send_to_amo(lead_id, response.text)
        else:
            print("⚠️ Google прислал пустой объект.")
            
    except Exception as e:
        print(f"💥 Ошибка внутри ai_worker: {str(e)}")

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