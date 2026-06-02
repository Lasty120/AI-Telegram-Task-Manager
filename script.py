import os

# Укажите путь к нужной папке ('.' — текущая папка)
root_dir = '.'
# Имя файла, куда всё запишется
output_file = 'result.txt'

# Список папок, в которые скрипт вообще НЕ БУДЕТ заходить
ignore_dirs = {'.venv', '.idea', '.git', '__pycache__'}

# Список расширений файлов, которые нужно ПРОПУСТИТЬ
ignore_extensions = {'.xml', '.json', '.txt', '.iml', '.pyc'}

with open(output_file, 'w', encoding='utf-8') as out_f:
    for root, dirs, files in os.walk(root_dir):

        # Модифицируем список dirs на месте, чтобы os.walk игнорировал эти папки
        dirs[:] = [d for d in dirs if d not in ignore_dirs]

        for file in files:
            # Пропускаем сам файл результата, чтобы он не записывал сам себя
            if file == output_file:
                continue

            # Проверяем расширение файла. Если оно в списке игнорируемых — пропускаем
            file_ext = os.path.splitext(file)[1].lower()
            if file_ext in ignore_extensions:
                continue

            file_path = os.path.join(root, file)

            # Пишем заголовок для файла в итоговый документ
            out_f.write(f"\n{'=' * 50}\n")
            out_f.write(f"ФАЙЛ: {file_path}\n")
            out_f.write(f"{'=' * 50}\n\n")

            try:
                # Читаем файл и записываем его содержимое
                with open(file_path, 'r', encoding='utf-8') as in_f:
                    content = in_f.read()
                    out_f.write(content)
                    out_f.write("\n")  # Добавляем пустую строку в конце
            except Exception as e:
                # Если файл бинарный (картинка, архив), пишем ошибку вместо содержимого
                out_f.write(f"[Не удалось прочитать файл. Ошибка: {e}]\n")

print(f"Готово! Содержимое файлов успешно сохранено в {output_file}")