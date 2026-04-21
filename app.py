import streamlit as st
import google.generativeai as genai
import os
from docx import Document
from io import BytesIO
import PyPDF2

# 1. ПЪРВОНАЧАЛНА КОНФИГУРАЦИЯ
st.set_page_config(page_title="Chitalishe AI Pro", page_icon="🏛️", layout="wide")

# 2. СИСТЕМА ЗА ВХОД
try:
    USERS = st.secrets["users"]
except:
    USERS = {"admin": "admin123"}


def check_password():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if st.session_state["authenticated"]:
        return True

    st.title("🔐 Вход в Chitalishe AI Pro")
    user = st.text_input("Потребителско име")
    password = st.text_input("Парола", type="password")

    if st.button("Влизане"):
        if user in USERS and USERS[user] == password:
            st.session_state["authenticated"] = True
            st.session_state["username"] = user
            st.rerun()
        else:
            st.error("❌ Грешно потребителско име или парола")
    return False


if not check_password():
    st.stop()


# 3. ПОМОЩНИ ФУНКЦИИ
def create_docx(text):
    doc = Document()
    doc.add_heading('Официален документ - Читалищен Секретар AI', 0)
    doc.add_paragraph(text)
    bio = BytesIO()
    doc.save(bio)
    bio.seek(0)
    return bio


def extract_text_from_pdf(pdf_file):
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            content = page.extract_text()
            if content:
                text += content
        return text
    except Exception as e:
        return f"Грешка при четене на PDF: {str(e)}"


@st.cache_data
def get_global_knowledge():
    context = ""
    knowledge_dir = "ai_knowledge_base"
    if os.path.exists(knowledge_dir):
        files = [f for f in os.listdir(knowledge_dir) if f.endswith('.txt')]
        for filename in sorted(files):
            with open(os.path.join(knowledge_dir, filename), 'r', encoding='utf-8') as f:
                context += f"\nИЗТОЧНИК {filename}:\n{f.read()}\n"
    return context if context else "Няма налична базова информация за законите."


# 4. КОНФИГУРАЦИЯ НА ИИ (GEMINI)
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=API_KEY)

    instruction = """Ти си професионален софтуерен асистент за управление на читалища в България. 
    Твоята сила е, че комбинираш Закона за народните читалища (ЗНЧ) с локалните документи на потребителя.
    Отговаряй винаги на български език, професионално и структурирано."""

    model = genai.GenerativeModel('gemini-1.5-flash', system_instruction=instruction)
except Exception as e:
    st.error(f"Грешка при конфигурацията на Gemini: {e}")
    st.stop()

# 5. СТРАНИЧНА ЛЕНТА
st.sidebar.title(f"👤 {st.session_state['username']}")
if st.sidebar.button("Изход"):
    st.session_state["authenticated"] = False
    st.rerun()

st.sidebar.divider()
st.sidebar.subheader("🔐 Личен архив")
uploaded_files = st.sidebar.file_uploader(
    "Качете Устав, договори или протоколи:",
    type=['pdf', 'txt'],
    accept_multiple_files=True
)

local_context = ""
if uploaded_files:
    for uploaded_file in uploaded_files:
        if uploaded_file.name.endswith('.pdf'):
            local_context += f"\nДОКУМЕНТ: {uploaded_file.name}\n{extract_text_from_pdf(uploaded_file)}\n"
        else:
            local_context += f"\nДОКУМЕНТ: {uploaded_file.name}\n{uploaded_file.read().decode('utf-8')}\n"
    st.sidebar.success(f"✅ Заредени: {len(uploaded_files)} документа")

mode = st.sidebar.radio("Действие:", ["⚖️ Консултация и Търсене", "📝 Създаване на протокол"])

# 6. ОСНОВЕН ЕКРАН
st.title("🏛️ Читалищен Секретар AI")

if mode == "⚖️ Консултация и Търсене":
    st.info("Попитайте нещо за законите или вашите документи.")
    user_input = st.chat_input("Напишете вашия въпрос тук...")

    if user_input:
        with st.chat_message("user"):
            st.markdown(user_input)
        with st.chat_message("assistant"):
            with st.spinner("Анализирам базите данни..."):
                global_kb = get_global_knowledge()
                # Избягваме прекалено дълъг промпт, ако няма качени файлове
                full_prompt = f"КОНТЕКСТ ОТ ЗАКОНИТЕ:\n{global_kb}\n\nЛОКАЛНИ ДОКУМЕНТИ:\n{local_context if local_context else 'Няма качени локални документи.'}\n\nВЪПРОС: {user_input}"

                try:
                    response = model.generate_content(full_prompt)
                    st.markdown(response.text)
                    docx = create_docx(response.text)
                    st.download_button("📥 Изтегли като Word", data=docx, file_name="consultation.docx")
                except Exception as e:
                    st.error(f"Грешка при генериране: {e}")

else:
    st.subheader("📝 Генератор на протоколи")
    text_input = st.text_area("Поставете бележки от събранието или дневен ред:", height=200)

    if st.button("Генерирай официален документ"):
        if not text_input:
            st.warning("Моля, въведете текст или бележки.")
        else:
            with st.spinner("Оформям протокола..."):
                try:
                    final_prompt = f"Въз основа на този контекст:\n{local_context}\n\nНаправи професионален протокол от следните бележки: {text_input}"
                    response = model.generate_content(final_prompt)
                    st.markdown(response.text)
                    docx = create_docx(response.text)
                    st.download_button("📥 Изтегли готовия файл", data=docx, file_name="protocol_pro.docx")
                except Exception as e:
                    st.error(f"Грешка: {e}")