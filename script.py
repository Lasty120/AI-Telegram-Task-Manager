import os

# Укажите путь к нужной папке ('.' — текущая папка)
root_dir = '..'
# Имя файла, куда всё запишется
output_file = 'result.txt'

with open(output_file, 'w', encoding='utf-8') as out_f:
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            # Пропускаем сам файл результата, чтобы он не записывал сам себя
            if file == output_file:
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

print(f"Готово! Содержимое всех файлов успешно сохранено в {output_file}")