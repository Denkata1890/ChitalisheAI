import streamlit as st
import google.generativeai as genai
import os
import warnings
from docx import Document
from io import BytesIO


# 1. ФУНКЦИЯ ЗА СЪЗДАВАНЕ НА WORD ФАЙЛ
def create_docx(text):
    doc = Document()
    doc.add_heading('Официален документ - Читалищен Секретар AI', 0)
    doc.add_paragraph(text)
    bio = BytesIO()
    doc.save(bio)
    bio.seek(0)
    return bio


warnings.filterwarnings("ignore")

# 2. КОНФИГУРАЦИЯ НА ИИ
API_KEY = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=API_KEY)

# По-комплексна инструкция за двете роли
instruction = """Ти си професионален асистент на народните читалища. Имаш две основни роли:
1. ПРАВЕН КОНСУЛТАНТ: Отговаряш точно по ЗНЧ, цитирайки членове.
2. ЦИФРОВ ПРОТОКОЛИСТ: Получаваш транскрипция (текст) от събрание и я превръщаш в официален протокол. 
Извличаш: дата, присъстващи, дневен ред, резюме на дискусиите и ВСИЧКИ взети решения. 
Ако информацията е непълна, оставяш места за попълване [използвай скоби]."""

model = genai.GenerativeModel(
    model_name='models/gemini-2.5-flash',
    system_instruction=instruction
)


@st.cache_data
def get_knowledge_base():
    context = ""
    knowledge_dir = "ai_knowledge_base"
    if os.path.exists(knowledge_dir):
        files = sorted(os.listdir(knowledge_dir))
        for filename in files:
            with open(os.path.join(knowledge_dir, filename), 'r', encoding='utf-8') as f:
                context += f.read() + "\n\n"
    return context


# 3. ИНТЕРФЕЙС
st.set_page_config(page_title="ИИ Читалищен Секретар", page_icon="🏛️", layout="wide")

# СТРАНИЧНА ЛЕНТА
st.sidebar.title("⚙️ Настройки на асистента")
mode = st.sidebar.radio("Изберете режим:", ["⚖️ Правна консултация", "📝 Дигитален протоколист"])

st.sidebar.divider()
st.sidebar.info("В режим 'Протоколист' просто поставете текста от записа на вашето събрание в чата.")

# ОСНОВЕН ЕКРАН
st.title("🏛️ ИИ Асистент 'Читалищен Секретар'")

if mode == "⚖️ Правна консултация":
    st.subheader("Търсене в законите и администрацията")
    placeholder = "Напр. Какъв е мандатът на Настоятелството?"
else:
    st.subheader("Генератор на протоколи от събрания")
    st.write("Поставете суровия текст (транскрипция) от записа на вашето събрание по-долу:")
    placeholder = "Поставете текста от записа тук..."

user_input = st.chat_input(placeholder)

if user_input:
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Обработвам информацията..."):
            try:
                if mode == "⚖️ Правна консултация":
                    knowledge_base = get_knowledge_base()
                    prompt = f"Контекст: {knowledge_base}\n\nВъпрос: {user_input}"
                else:
                    prompt = f"ТОВА Е ЗАПИС ОТ СЪБРАНИЕ. Направи официален протокол въз основа на него:\n\n{user_input}"

                response = model.generate_content(prompt)
                answer = response.text

                st.markdown(answer)

                st.divider()
                docx_file = create_docx(answer)
                st.download_button(
                    label="📥 Изтегли като готов Протокол (Word)",
                    data=docx_file,
                    file_name="protocol_chitalishte.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
            except Exception as e:
                st.error(f"Грешка: {e}")