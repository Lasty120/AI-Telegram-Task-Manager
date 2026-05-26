import re
from datetime import datetime, timedelta

import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


def handle_message(text: str) -> tuple[str, int | None]:
    time_match = re.search(r'(\d{1,2})[.:](\d{2})', text)

    if not time_match:
        time_str = "Время не найдено"
        target_timestamp = None
    else:
        hours = int(time_match.group(1))
        minutes = int(time_match.group(2))
        time_str = f"{hours:02d}:{minutes:02d}"

        # Явно указываем часовой пояс Алматы (с 2024 года в Алматы UTC+5)
        tz_almaty = ZoneInfo("Asia/Almaty")

        # Получаем текущее время именно в Алматы
        now = datetime.now(tz_almaty)

        # Подставляем часы и минуты, введенные пользователем
        target_time = now.replace(hour=hours, minute=minutes, second=0, microsecond=0)

        # Если это время в Алматы сегодня уже прошло, переносим на завтра
        if target_time < now:
            target_time += timedelta(days=1)

        # .timestamp() в Python автоматически переведет дату из часового пояса
        # Asia/Almaty в глобальный UTC-timestamp (число секунд с 1970 года)
        target_timestamp = int(target_time.timestamp())

    cleaned_text = re.sub(r'(\d{1,2})[.:](\d{2})', '', text)
    cleaned_text = ' '.join(cleaned_text.split())

    bot_output = (
        f"Ваше задание сохранено\n"
        f"*{cleaned_text}*\n"
        f"Время: {time_str}"
    )

    return bot_output, target_timestamp