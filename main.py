import os
import requests
import time
import threading
from flask import Flask, request

app = Flask(__name__)

# Инициализируем переменные из окружения
SUBDOMAIN = os.environ.get("SUBDOMAIN", "restartivanovo")
CLIENT_ID = os.environ.get("CLIENT_ID")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET")
# Эти переменные будут обновляться в памяти процесса
current_access_token = os.environ.get("AMO_TOKEN")
current_refresh_token = os.environ.get("REFRESH_TOKEN")

def refresh_amo_token():
    """Функция автоматического обновления токена"""
    global current_access_token, current_refresh_token
    print("🔄 Обновляю токен amoCRM...")
    
    url = f"https://{SUBDOMAIN}.amocrm.ru/oauth2/access_token"
    payload = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "refresh_token",
        "refresh_token": current_refresh_token,
        "redirect_uri": "https://amo-djr3.onrender.com" # Твой URL
    }
    
    try:
        res = requests.post(url, json=payload, timeout=10)
        if res.status_code == 200:
            data = res.json()
            current_access_token = data['access_token']
            current_refresh_token = data['refresh_token']
            print("✅ Токены успешно обновлены!")
            return True
        else:
            print(f"❌ Ошибка обновления токена: {res.text}")
            return False
    except Exception as e:
        print(f"💥 Сбой при запросе токена: {e}")
        return False

def send_note_to_amo(lead_id, advice_text, retry=True):
    """Отправка примечания с проверкой на 401"""
    global current_access_token
    url = f"https://{SUBDOMAIN}.amocrm.ru/api/v4/leads/{lead_id}/notes"
    headers = {
        "Authorization": f"Bearer {current_access_token}",
        "Content-Type": "application/json"
    }
    payload = [{"note_type": "common", "params": {"text": f"🤖 Gemini Flash: {advice_text}"}}]
    
    res = requests.post(url, json=payload, headers=headers, timeout=10)
    
    if res.status_code == 401 and retry:
        print("⚠️ Токен протух (401). Пробую обновить...")
        if refresh_amo_token():
            # Повторяем отправку с новым токеном
            return send_note_to_amo(lead_id, advice_text, retry=False)
    
    if res.status_code == 200:
        print(f"✅ Совет добавлен в сделку {lead_id}")
    else:
        print(f"❌ Ошибка amoCRM ({res.status_code}): {res.text}")

def process_ai_logic(lead_id, client_text):
    """Запрос к Gemini и запуск отправки"""
    api_key = os.environ.get("GEMINI_KEY").strip()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    payload = {"contents": [{"parts": [{"text": f"Дай 1 короткий совет менеджеру по ремонту на запрос: {client_text}"}]}]}
    
    try:
        response = requests.post(url, json=payload, timeout=25)
        if response.status_code == 200:
            advice = response.json()['candidates'][0]['content']['parts'][0]['text']
            send_note_to_amo(lead_id, advice)
        else:
            print(f"❌ Ошибка Gemini ({response.status_code})")
    except Exception as e:
        print(f"💥 Сбой Gemini: {e}")

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.form.to_dict()
    lead_id = data.get('message[add][0][entity_id]') or data.get('leads[update][0][id]')
    text = data.get('message[add][0][text]') or data.get('leads[update][0][name]')

    if lead_id and text:
        if "входящий" in text.lower(): return "OK", 200
        threading.Thread(target=process_ai_logic, args=(lead_id, text)).start()
    
    return "OK", 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))