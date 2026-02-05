import os
import requests
from flask import Flask, request
from google import genai

app = Flask(__name__)

GEMINI_KEY = os.environ.get("GEMINI_KEY")
AMO_TOKEN = os.environ.get("AMO_TOKEN")
SUBDOMAIN = "restartivanovo"

client = genai.Client(api_key=GEMINI_KEY)

def get_chat_history(entity_id):
    """Получает ВСЮ доступную историю переписки из карточки"""
    # Запрашиваем события (events), так как там хранится переписка из чатов
    url = f"https://{SUBDOMAIN}.amocrm.ru/api/v4/events?filter[entity_id]={entity_id}&filter[entity_type]=lead"
    headers = {"Authorization": f"Bearer {AMO_TOKEN}"}
    
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            events = res.json().get('_embedded', {}).get('events', [])
            history = ""
            for ev in events:
                # Фильтруем только сообщения из чатов (входящие и исходящие)
                if ev['type'] in ['incoming_chat_message', 'outgoing_chat_message']:
                    # Извлекаем текст сообщения из вложенных структур
                    msg_text = ev.get('value_after', [{}])[0].get('message', {}).get('text', '')
                    role = "Клиент" if ev['type'] == 'incoming_chat_message' else "Менеджер"
                    if msg_text:
                        history += f"{role}: {msg_text}\n"
            return history if history else "История пуста (начало диалога)."
    except Exception as e:
        print(f"❌ Ошибка получения истории: {e}")
    return "Не удалось загрузить историю."

def get_ai_advice(history, current_text):
    try:
        # Улучшенный промпт для глубокого анализа
        prompt = f"""
        Ты — аналитик и коуч по продажам. Перед тобой ПОЛНАЯ история переписки.
        
        ИСТОРИЯ ДИАЛОГА:
        {history}
        
        ПОСЛЕДНЕЕ СООБЩЕНИЕ:
        {current_text}
        
        ЗАДАЧА:
        1. Проанализируй, на каком этапе сделка.
        2. Если менеджер упустил вопрос клиента — укажи на это.
        3. Дай конкретную фразу для следующего ответа, чтобы приблизить продажу.
        
        СОВЕТ (кратко):
        """
        
        response = client.models.generate_content(
            model="gemini-3-flash-preview", 
            contents=prompt
        )
        return response.text.strip() if response.text else None
    except Exception as e:
        print(f"❌ Ошибка Gemini: {e}")
    return None

# Остальные функции (send_to_amo, webhook) остаются без изменений

