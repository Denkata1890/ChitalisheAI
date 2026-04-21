import streamlit as st
import google.generativeai as genai
import os
from docx import Document
from io import BytesIO
import PyPDF2

# 1. КОНФИГУРАЦИЯ НА СТРАНИЦАТА
st.set_page_config(page_title="Chitalishe AI Pro", page_icon="🏛️", layout="wide")


# 2. СИСТЕМА ЗА ВХОД (ИЗЧИСТЕНА)
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if st.session_state["authenticated"]:
        return True

    st.title("🔐 Вход в Chitalishe AI Pro")
    user = st.text_input("Потребителско име")
    password = st.text_input("Парола", type="password")

    if st.button("Влизане"):
        if "users" in st.secrets and user in st.secrets["users"] and st.secrets["users"][user] == password:
            st.session_state["authenticated"] = True
            st.session_state["username"] = user
            st.rerun()
        else:
            st.error("❌ Грешно потребителско име или парола")
    return False


if not check_password():
    st.stop()

# 3. ПОКАЗВАНЕ НА ПОТРЕБИТЕЛЯ
if st.session_state["username"] == "admin":
    st.sidebar.warning("🛠️ Влезли сте като Администратор.")
else:
    st.sidebar.info(f"🏛️ Добре дошли, {st.session_state['username']}")

st.sidebar.write(f"👤 Вписани сте като: **{st.session_state['username']}**")
if st.sidebar.button("Изход"):
    st.session_state["authenticated"] = False
    st.rerun()


# 4. ПОМОЩНИ ФУНКЦИИ
def create_docx(text):
    doc = Document()
    doc.add_heading('Официален документ - Читалищен Секретар AI', 0)
    doc.add_paragraph(text)
    bio = BytesIO()
    doc.save(bio)
    bio.seek(0)
    return bio


def extract_text_from_pdf(pdf_file):
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text


# 5. КОНФИГУРАЦИЯ НА GEMINI
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=API_KEY)

    instruction = """Ти си професионален софтуерен асистент за управление на читалища. 
    Твоята сила е, че комбинираш ОБЩИТЕ ЗАКОНИ (ЗНЧ) с ЛОКАЛНИЯ АРХИВ на читалището."""

    model = genai.GenerativeModel('gemini-1.5-flash', system_instruction=instruction)
except Exception as e:
    st.error(f"Грешка при зареждане на ИИ: {e}")


# 6. ЗАРЕЖДАНЕ НА ЗАКОНИТЕ
@st.cache_data
def get_global_knowledge():
    context = ""
    knowledge_dir = "ai_knowledge_base"
    if os.path.exists(knowledge_dir):
        for filename in sorted(os.listdir(knowledge_dir)):
            with open(os.path.join(knowledge_dir, filename), 'r', encoding='utf-8') as f:
                context += f"ИЗТОЧНИК {filename}:\n{f.read()}\n\n"
    return context


# 7. УПРАВЛЕНИЕ НА ЛОКАЛНИЯ АРХИВ (SIDEBAR)
st.sidebar.title("🔐 Личен архив")
uploaded_files = st.sidebar.file_uploader(
    "Качете документи (PDF/TXT):",
    type=['pdf', 'txt'],
    accept_multiple_files=True
)

local_context = ""
if uploaded_files:
    st.sidebar.success(f"Заредени са {len(uploaded_files)} документа.")
    for uploaded_file in uploaded_files:
        if uploaded_file.name.endswith('.pdf'):
            local_context += f"\nДОКУМЕНТ ({uploaded_file.name}):\n" + extract_text_from_pdf(uploaded_file)
        else:
            local_context += f"\nДОКУМЕНТ ({uploaded_file.name}):\n" + str(uploaded_file.read(), "utf-8")

# 8. ОСНОВЕН ПАНЕЛ
mode = st.sidebar.radio("Действие:", ["⚖️ Консултация", "📝 Създаване на протокол"])

st.title("🏛️ Читалищен Секретар AI")

if mode == "⚖️ Консултация":
    st.info("Анализ на закони и ваши документи.")
    user_input = st.chat_input("Задайте въпрос...")

    if user_input:
        with st.chat_message("user"): st.markdown(user_input)
        with st.chat_message("assistant"):
            with st.spinner("Проверявам..."):
                global_kb = get_global_knowledge()
                full_prompt = f"ЗАКОНИ:\n{global_kb}\n\nАРХИВ:\n{local_context}\n\nВЪПРОС: {user_input}"
                response = model.generate_content(full_prompt)
                st.markdown(response.text)
                docx = create_docx(response.text)
                st.download_button("📥 Изтегли Word", data=docx, file_name="consultation.docx")

else:
    st.subheader("Генератор на протоколи")
    text_input = st.text_area("Поставете текст от събранието тук:", height=150)

    if st.button("Генерирай протокол"):
        if text_input:
            with st.spinner("Генерирам..."):
                prompt = f"Използвай архив за контекст:\n{local_context}\n\nНаправи протокол от това събрание: {text_input}"
                response = model.generate_content(prompt)
                st.markdown(response.text)
                docx = create_docx(response.text)
                st.download_button("📥 Изтегли Word", data=docx, file_name="protocol.docx")