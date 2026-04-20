import re
import os


def clean_law_text(text):

    text = re.sub(r'\s+', ' ', text)

    text = re.sub(r'[^\w\s\.,\?\!\-\"„“\(\):;]', '', text)
    return text.strip()


def create_chunks(text, chunk_size=1000, overlap=200):
    """Нарязва текста на парчета (chunks) за по-добра работа на ИИ."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start += (chunk_size - overlap)
    return chunks


def process_law_file(input_filename, output_folder):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    try:
        with open(input_filename, 'r', encoding='utf-8') as f:
            raw_content = f.read()


        cleaned_text = clean_law_text(raw_content)


        chunks = create_chunks(cleaned_text)


        for i, chunk in enumerate(chunks):
            chunk_name = os.path.join(output_folder, f"chunk_{i + 1}.txt")
            with open(chunk_name, 'w', encoding='utf-8') as f:
                # Добавяме метаданни в началото на всеки файл за ИИ контекст
                f.write(f"ИЗТОЧНИК: {input_filename}\n")
                f.write("-" * 20 + "\n")
                f.write(chunk)

        print(f"Успех! Създадени са {len(chunks)} парчета в папка '{output_folder}'.")

    except FileNotFoundError:
        print("Грешка: Файлът не е намерен. Провери името.")



process_law_file('zakon.txt', 'ai_knowledge_base')