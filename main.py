import os
import requests
import threading
from flask import Flask, request
from google import genai

app = Flask(__name__)

# --- Конфигурация из Render Environment Variables ---
GEMINI_KEY = os.environ.get("GEMINI_KEY")
AMO_TOKEN = os.environ.get("AMO_TOKEN")
SUBDOMAIN = "restartivanovo"

# Инициализация клиента Google по стандартам 2026 года
client_ai = genai.Client(api_key=GEMINI_KEY, http_options={'api_version': 'v1beta'})

def ai_worker(lead_id, client_text):
    """
    Фоновая задача для работы с Gemini.
    Используем модель 'gemini-1.5-flash', которая является самой стабильной.
    """
    try:
        print(f"🚀 Запрос к Gemini для сделки {lead_id}...")
        
        # Согласно ai.google.dev, теперь это самый надежный метод
        response = client_ai.models.generate_content(
            model='gemini-1.5-flash',
            contents=f"Ты эксперт сервисного центра. Дай 1 очень короткий совет менеджеру по запросу: {client_text}"
        )

        if response and response.text:
            advice = response.text.strip()
            print(f"✅ ИИ ответил: {advice[:50]}...")
            send_to_amo(lead_id, advice)
        else:
            print("⚠️ ИИ вернул пустой ответ.")

    except Exception as e:
        print(f"❌ Ошибка Gemini: {e}")

def send_to_amo(lead_id, text):
    """Отправка примечания в amoCRM"""
    url = f"https://{SUBDOMAIN}.amocrm.ru/api/v4/leads/{lead_id}/notes"
    headers = {
        "Authorization": f"Bearer {AMO_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = [{"note_type": "common", "params": {"text": f"🤖 Gemini: {text}"}}]
    
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=10)
        print(f"📤 Результат amoCRM: {res.status_code}")
    except Exception as e:
        print(f"💥 Ошибка при отправке в amoCRM: {e}")

@app.route('/webhook', methods=['POST'])
def webhook():
    # Получаем данные от вебхука amoCRM
    data = request.form.to_dict()
    
    # Извлекаем ID сделки и текст последнего сообщения
    lead_id = data.get('message[add][0][entity_id]') or data.get('leads[update][0][id]')
    text = data.get('message[add][0][text]') or data.get('leads[update][0][name]')

    if lead_id and text:
        # Игнорируем технические сообщения
        if "входящий" in text.lower() and "успешный" in text.lower():
            return "OK", 200

        # Запускаем обработку в отдельном потоке
        threading.Thread(target=ai_worker, args=(lead_id, text)).start()
    
    return "OK", 200

if __name__ == "__main__":
    # Порт для Render
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
