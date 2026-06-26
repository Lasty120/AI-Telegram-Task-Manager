# -*- coding: utf-8 -*-
"""
Утилиты для работы с Notion.
Содержит функции для фильтрации и обработки данных, получаемых из Notion API.
"""

def filter_done_statuses(statuses: list[str]) -> list[str]:
    """
    Фильтрует список статусов/селектов, исключая те, которые
    начинаются на 'done' (без учета регистра и пробелов по краям).

    :param statuses: Исходный список названий статусов.
    :return: Отфильтрованный список статусов.
    """
    if not statuses:
        return []
    
    # Фильтруем элементы: убираем пробелы по краям, переводим в нижний регистр 
    # и проверяем, не начинается ли строка на "done".
    return [
        status for status in statuses 
        if not (status and status.strip().lower().startswith("done"))
    ]
