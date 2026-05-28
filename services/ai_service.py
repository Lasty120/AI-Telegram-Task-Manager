from openai import AsyncOpenAI
from pydantic import ValidationError
from datetime import datetime
import pytz

from config import OPENAI_DEFAULT_MODEL, OPENAI_API_KEY, OPENAI_DEFAULT_URL
from database.schemas import MultiTaskActionSchema
from services.prompts import get_system_prompt

client = AsyncOpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_DEFAULT_URL)


async def parse_user_text(user_text: str, user_tasks: list = None) -> MultiTaskActionSchema | str:
    # ИИ обязан знать текущее время, чтобы правильно рассчитать даты
    tz = pytz.timezone('Asia/Almaty')  # Замени на нужный
    current_time = datetime.now(tz).strftime("%Y-%m-%d %H:%M")

    system_prompt = get_system_prompt(current_time)

    # Форматируем и передаем список задач
    import json
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
        response = await client.chat.completions.create(
            model=OPENAI_DEFAULT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text}
            ],
            temperature=0.1,  # Делаем ИИ максимально "сухим" и точным
            response_format={"type": "json_object"}
        )

        ai_text = response.choices[0].message.content
        print(ai_text)
        return MultiTaskActionSchema.model_validate_json(ai_text)

    except ValidationError as ve:
        return f"❌ Ошибка парсинга: {ve}"
    except Exception as e:
        return f"❌ Ошибка API: {e}"