# -*- coding: utf-8 -*-
"""
Утилиты для работы с Notion.
Содержит функции для фильтрации и обработки данных, получаемых из Notion API.
"""

# Ключевые слова, по которым определяется поле «Важность» (регистронезависимо).
# Поддерживаются русский, казахский и английский варианты названий.
_IMPORTANCE_KEYWORDS: tuple[str, ...] = (
    "важность",
    "приоритет",
    "priority",
    "importance",
    "маңыздылық",   # казахский — «важность»
    "басымдық",     # казахский — «приоритет»
)


def is_importance_prop(name: str) -> bool:
    """
    Проверяет, относится ли название свойства к полю «Важность».
    Сравнение регистронезависимое; учитываются пробелы по краям.

    :param name: Название свойства из схемы базы данных Notion.
    :return: True, если название начинается с одного из ключевых слов.
    """
    normalized = name.strip().lower()
    return any(normalized.startswith(kw) for kw in _IMPORTANCE_KEYWORDS)


def find_importance_prop(db_props: dict) -> str | None:
    """
    Находит ключ (название) первого select-свойства в схеме БД Notion,
    которое соответствует полю «Важность» по ключевым словам.

    В отличие от наивного поиска «первый select», этот метод:
      - сначала ищет select-поле с «правильным» именем;
      - только если такого нет — возвращает None, не выбирая произвольное поле.

    :param db_props: Словарь {название_свойства: тип_свойства} из схемы БД.
    :return: Название найденного свойства или None.
    """
    return next(
        (
            name
            for name, prop_type in db_props.items()
            if prop_type == "select" and is_importance_prop(name)
        ),
        None,
    )


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
