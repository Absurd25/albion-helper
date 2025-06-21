import os

def collect_python_files(root_dir):
    """Возвращает список всех .py-файлов в указанной директории."""
    python_files = []
    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename.endswith(".py"):
                full_path = os.path.join(dirpath, filename)
                if not(full_path in ('D:\\X3\\Python\\Project\\albion\\help bot\\albion_helper\\all_file_to_txt\\mainn.py','D:\\X3\\Python\\Project\\albion\\help bot\\albion_helper\\config\\read_json.py')):
                    python_files.append(full_path)
    return python_files

def generate_output_file(output_path, root_dir):
    """Генерирует txt-файл с содержимым всех .py-файлов."""
    try:
        with open(output_path, "w", encoding="utf-8") as output_file:
            files = collect_python_files(root_dir)

            print(f"✅ Найдено .py файлов: {len(files)}")
            for file_path in files:
                relative_path = os.path.relpath(file_path, root_dir)
                print(f"📄 Записываю: {relative_path}")

                output_file.write(f"--- {relative_path} ---\n\n")

                with open(file_path, "r", encoding="utf-8") as py_file:
                    content = py_file.read()
                    output_file.write(content + "\n\n")
        print(f"📁 Содержимое успешно сохранено в: {output_path}")
    except Exception as e:
        print(f"❌ Ошибка при записи файла: {e}")


project_root = os.path.abspath("../")
output_txt = os.path.abspath("all_python_files.txt")

print(f"🔍 Ищем проект в: {project_root}")
generate_output_file(output_txt, project_root)