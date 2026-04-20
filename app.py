import streamlit as st
import google.generativeai as genai
import os
import warnings
from docx import Document
from io import BytesIO


# 1. ФУНКЦИЯ ЗА СЪЗДАВАНЕ НА WORD ФАЙЛ
def create_docx(text):
    doc = Document()
    # Добавяме заглавие в самия документ
    doc.add_heading('Генериран документ от ИИ Читалищен Секретар', 0)
    doc.add_paragraph(text)
    bio = BytesIO()
    doc.save(bio)
    bio.seek(0)
    return bio


warnings.filterwarnings("ignore")

# 2. КОНФИГУРАЦИЯ НА ИИ (С добавени системни инструкции)
API_KEY = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=API_KEY)

# Тук казваме на ИИ какъв е неговият характер и задачи
instruction = """Ти си професионален правен консултант на народните читалища в България. 
Твоята задача е да отговаряш на въпроси по ЗНЧ и да СЪСТАВЯШ официални документи (протоколи, заповеди, покани). 
Когато съставяш документ, го прави в официален формат с места за дата, подписи и изходящи номера. 
Винаги цитирай конкретни членове от законите, предоставени в контекста."""

model = genai.GenerativeModel(
    model_name='models/gemini-2.5-flash',
    system_instruction=instruction
)


# 3. КЕШИРАНЕ НА БАЗАТА ДАННИ
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


# 4. ИНТЕРФЕЙС
st.set_page_config(page_title="ИИ Читалищен Секретар", page_icon="🏛️")

st.title("🏛️ ИИ Асистент 'Читалищен Секретар'")
st.subheader("Правен консултант по ЗНЧ и администрация")

# По-модерен чат вход вместо st.text_input
user_input = st.chat_input("Задайте въпрос или поискайте документ (напр. 'Напиши покана за ОС')")

if user_input:
    # Показваме въпроса на потребителя в балонче
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Анализирам законите и пиша..."):
            try:
                knowledge_base = get_knowledge_base()
                # Изпращаме контекста и въпроса
                prompt = f"Използвай този контекст:\n{knowledge_base}\n\nВъпрос от потребителя: {user_input}"

                response = model.generate_content(prompt)
                answer = response.text

                st.markdown(answer)

                # ЛОГИКА ЗА ИЗТЕГЛЯНЕ
                st.divider()
                docx_file = create_docx(answer)

                st.download_button(
                    label="📄 Изтегли като Word документ",
                    data=docx_file,
                    file_name="chitalishte_doc.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    icon="📥"
                )

                st.info("💡 Можете да редактирате изтегления файл в Microsoft Word или Google Docs.")
            except Exception as e:
                st.error(f"Възникна грешка при връзката с ИИ: {e}")

# СТРАНИЧНА ЛЕНТА
st.sidebar.title("Меню")
st.sidebar.info("Този асистент използва актуалната база данни от закони, заредена в системата.")
if st.sidebar.button("Изчисти историята"):
    st.rerun()