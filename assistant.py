import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
import os
os.environ['GRPC_VERBOSITY'] = 'ERROR'
import google.generativeai as genai
import os


API_KEY = "AIzaSyD18c9EqBzeaxlnuFWJxGDZDITtxObqAT8"
genai.configure(api_key=API_KEY)


def ask_ai_with_context(question):

    context = ""
    knowledge_dir = "ai_knowledge_base"

    if os.path.exists(knowledge_dir):

        files = sorted(os.listdir(knowledge_dir))
        for filename in files:
            with open(os.path.join(knowledge_dir, filename), 'r', encoding='utf-8') as f:
                context += f.read() + "\n\n"
    else:
        return "Грешка: Не намерих папка със закони. Моля, пусни първо processor.py!"


    model = genai.GenerativeModel('models/gemini-2.5-flash')


    prompt = f"""
    Ти си специализиран ИИ асистент за българските народни читалища. 
    Твоята задача е да помагаш на секретарите с административни и юридически въпроси.

    ИЗПОЛЗВАЙ ТОЗИ ТЕКСТ ОТ ЗАКОНИТЕ:
    {context}

    ВЪПРОС: {question}

    ИНСТРУКЦИИ:
    1. Отговаряй само въз основа на предоставения текст.
    2. Винаги цитирай номер на член от закона (напр. "Според Чл. 14...").
    3. Бъди кратък и професионален.
    """

    response = model.generate_content(prompt)
    return response.text


# --- ИЗПЪЛНЕНИЕ ---
if __name__ == "__main__":
    print("--- ИИ Асистент 'Читалищен Секретар' 2026 ---")
    user_query = input("Вашият въпрос: ")
    print("\nАнализирам законите и генерирам отговор...\n")

    try:
        result = ask_ai_with_context(user_query)
        print("-" * 40)
        print(result)
        print("-" * 40)
    except Exception as e:
        print(f"Възникна грешка при комуникацията: {e}")