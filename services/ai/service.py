from openai import AsyncOpenAI
from pydantic import ValidationError
from datetime import datetime, timedelta
import json

import re

from config import OPENAI_DEFAULT_MODEL, OPENAI_API_KEY, OPENAI_DEFAULT_URL, TIMEZONE
from database.schemas import MultiTaskActionSchema
from services.ai.prompts import get_system_prompt
from utils.formatters import compute_local_indices
# Проверка задач без срока — передаём ИИ null вместо "2060-01-01"
from utils.date_utils import is_fallback_timestamp

client = AsyncOpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_DEFAULT_URL)


async def parse_user_text(user_text: str, user_tasks: list = None, user = None) -> MultiTaskActionSchema | str:
    # ИИ обязан знать текущее время, чтобы правильно рассчитать даты
    tz = TIMEZONE
    current_time = datetime.now(tz).strftime("%Y-%m-%d %H:%M")

    statuses = []
    multi_selects = []
    if user:
        try:
            if user["notion_statuses"]:
                statuses = json.loads(user["notion_statuses"])
        except Exception:
            pass
        try:
            if user["notion_multi_selects"]:
                multi_selects = json.loads(user["notion_multi_selects"])
        except Exception:
            pass

    system_prompt = get_system_prompt(current_time, statuses, multi_selects)

    # Форматируем и передаем список задач

    tasks_list = []
    if user_tasks:
        local_indices = compute_local_indices(user_tasks, tz)
        for task in user_tasks:
            try:
                task_time = datetime.fromtimestamp(task['time'], tz)
                # Задачи без срока не показываем ИИ как "2060-01-01" — передаём null
                if is_fallback_timestamp(task['time']):
                    formatted_time = None
                    formatted_ends_at = None
                else:
                    formatted_time = task_time.strftime("%Y-%m-%d %H:%M")
                    # Рассчитываем ends_at только для задач с реальным сроком
                    duration = task["duration"] if "duration" in task.keys() else None
                    if duration:
                        ends_at_time = task_time + timedelta(minutes=duration)
                        formatted_ends_at = ends_at_time.strftime("%Y-%m-%d %H:%M")
                    else:
                        formatted_ends_at = None
                duration = task["duration"] if "duration" in task.keys() else None
                importance = task["importance"] if "importance" in task.keys() else None

            except Exception:
                formatted_time = None
                formatted_ends_at = None
                duration = None
                importance = None
                
            tasks_list.append({
                "task_id": task["id"],
                "position": local_indices.get(task["id"]),
                "content": task["content"],
                "details": task["details"],
                "time": formatted_time,
                "duration": duration,
                "ends_at": formatted_ends_at,
                "importance": importance,
                "notion_added": bool(task["notion_added"]) if "notion_added" in task.keys() else False,
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
            temperature=0.0,  # Ставим 0.0 для максимальной детерминированности
            response_format={"type": "json_object"}
        )

        ai_text = response.choices[0].message.content
        print(f"Сырой ответ ИИ:\n{ai_text}") # Оставь для дебага

        # 🛠 ОЧИСТКА МУСОРА: Удаляем Markdown-обертки (```json ... ```)
        # и лишние символы до первого { и после последнего }
        clean_json = re.sub(r"^```[a-zA-Z]*\n|```$", "", ai_text.strip(), flags=re.MULTILINE)

        # На случай, если модель все равно вставила текст до/после JSON
        start_idx = clean_json.find('{')
        end_idx = clean_json.rfind('}')
        if start_idx != -1 and end_idx != -1:
            clean_json = clean_json[start_idx:end_idx+1]

        return MultiTaskActionSchema.model_validate_json(clean_json)

    except ValidationError as ve:
        return f"❌ Ошибка парсинга: {ve}"
    except Exception as e:
        return f"❌ Ошибка API: {e}"