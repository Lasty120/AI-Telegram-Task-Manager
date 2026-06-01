import json
from datetime import datetime
import pytz
import google.generativeai as genai
from pydantic import ValidationError
from os import getenv
from dotenv import load_dotenv



from database.schemas import MultiTaskActionSchema
from services.ai.prompts import get_system_prompt


async def parse_user_text(user_text: str, user_tasks: list = None) -> MultiTaskActionSchema | str:
    tz = pytz.timezone('Asia/Almaty')
    current_time = datetime.now(tz).strftime("%Y-%m-%d %H:%M")

    system_prompt = get_system_prompt(current_time)

    # Сборка текущих задач в JSON-строку
    tasks_list = []
    if user_tasks:
        for task in user_tasks:
            try:
                task_time = datetime.fromtimestamp(task['time'], tz)
                formatted_time = task_time.strftime("%Y-%m-%d %H:%M")
            except Exception:
                formatted_time = None
            tasks_list.append({
                "task_id": task["id"],
                "content": task["content"],
                "details": task["details"],
                "time": formatted_time
            })
    tasks_json = json.dumps(tasks_list, ensure_ascii=False, indent=2)
    system_prompt += f"\n\n<user tasks>\n{tasks_json}\n</user tasks>"

    try:
        # Инициализируем модель (Flash — быстрая и умная)
        model = genai.GenerativeModel(
            model_name='gemini-1.5-flash',
            system_instruction=system_prompt # Системный промпт отдается красиво, отдельным полем
        )

        # Вызываем асинхронную генерацию
        response = await model.generate_content_async(
            contents=user_text,
            generation_config=genai.types.GenerationConfig(
                temperature=0.1,
                response_mime_type="application/json",
                # 🔥 МАГИЯ: Заставляем модель строго следовать твоей Pydantic схеме
                response_schema=MultiTaskActionSchema
            )
        )

        ai_text = response.text
        print("✅ Быстрый ответ от Gemini получен!")
        print(ai_text)

        return MultiTaskActionSchema.model_validate_json(ai_text)

    except ValidationError as ve:
        return f"❌ Ошибка парсинга: {ve}"
    except Exception as e:
        return f"❌ Ошибка Gemini API: {e}"