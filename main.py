import os
import requests
from flask import Flask, request

# Используем актуальный импорт для новой библиотеки Google GenAI
try:
    from google import genai
except ImportError:
    # На случай если библиотека установлена иначе
    import google.generativeai as genai

app = Flask(__name__)

# --- Конфигурация ---
GEMINI_KEY = os.environ.get("GEMINI_KEY")
AMO_TOKEN = os.environ.get("AMO_TOKEN")
SUBDOMAIN = "restartivanovo"

client = genai.Client(api_key=GEMINI_KEY)

def get_chat_history(entity_id):
    """Получает историю сообщений чата из событий сделки"""
    url = f"https://{SUBDOMAIN}.amocrm.ru/api/v4/events?filter[entity_id]={entity_id}&filter[entity_type]=lead"
    headers = {"Authorization": f"Bearer {AMO_TOKEN}"}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            events = res.json().get('_embedded', {}).get('events', [])
            history = ""
            for ev in events:
                if ev['type'] in ['incoming_chat_message', 'outgoing_chat_message']:
                    try:
                        # amoCRM глубоко прячет текст сообщения в событиях
                        val = ev.get('value_after', [{}])[0]
                        msg_text = val.get('message', {}).get('text', '')
                        role = "Клиент" if ev['type'] == 'incoming_chat_message' else "Менеджер"
                        if msg_text:
                            history += f"{role}: {msg_text}\n"
                    except: continue
            return history if history else "История пуста."
    except Exception as e:
        print(f"❌ Ошибка получения истории: {e}")
    return "История недоступна."

def get_ai_advice(history, current_text):
    """Запрос к ИИ с полным контекстом чата"""
    try:
        prompt = f"""
        Ты — эксперт-наставник по продажам в CRM. 
        Проанализируй историю диалога и последнее сообщение. 
        Дай менеджеру совет, как закрыть сделку.
        
        ИСТОРИЯ ЧАТА:
        {history}
        
        ПОСЛЕДНЕЕ СООБЩЕНИЕ:
        {current_text}
        
        СОВЕТ (макс 2 фразы):
        """
        response = client.models.generate_content(
            model="gemini-3-flash-preview", 
            contents=prompt
        )
        return response.text.strip() if response.text else None
    except Exception as e:
        print(f"❌ Ошибка Gemini: {e}")
        return None

def send_to_amo(lead_id, advice):
    """Отправка совета в карточку сделки"""
    url = f"https://{SUBDOMAIN}.amocrm.ru/api/v4/leads/{lead_id}/notes"
    headers = {
        "Authorization": f"Bearer {AMO_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = [{"note_type": "common", "params": {"text": f"🤖 ИИ-Советник: {advice}"}}]
    requests.post(url, json=payload, headers=headers, timeout=10)

# Главная страница для проверки (чтобы не было 404 на основном домене)
@app.route('/')
def home():
    return "AI Assistant is Online!", 200

# ИСПРАВЛЕННЫЙ РОУТ ВЕБХУКА
@app.route('/webhook', methods=['POST', 'GET'])
def webhook():
    if request.method == 'GET':
        return "Webhook point is active. Use POST.", 200
        
    # amoCRM шлет данные в формате Form Data
    data = request.form.to_dict()
    
    # Пытаемся найти ID сделки и текст сообщения в разных ключах
    lead_id = (data.get('message[add][0][entity_id]') or 
               data.get('leads[update][0][id]') or 
               data.get('leads[add][0][id]'))
               
    text = (data.get('message[add][0][text]') or 
            data.get('leads[update][0][name]') or 
            "Обновление сделки")

    if lead_id:
        history = get_chat_history(lead_id)
        advice = get_ai_advice(history, text)
        if advice:
            send_to_amo(lead_id, advice)
            print(f"✅ Успешно обработана сделка {lead_id}")
            return "OK", 200
    
    print("⚠️ Вебхук получен, но ID сделки не найден в данных.")
    return "No lead ID found", 200

if __name__ == "__main__":
    # Render передает порт в переменную окружения
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
