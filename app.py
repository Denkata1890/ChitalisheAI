import streamlit as st
import google.generativeai as genai
import os
from docx import Document
from io import BytesIO
import PyPDF2


# 1. ПОМОЩНИ ФУНКЦИИ
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


# 2. КОНФИГУРАЦИЯ НА ИИ
API_KEY = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=API_KEY)

instruction = """Ти си професионален софтуерен асистент за управление на читалища. 
Твоята сила е, че комбинираш ОБЩИТЕ ЗАКОНИ (ЗНЧ) с ЛОКАЛНИЯ АРХИВ (Устав, заповеди, договори) на конкретното читалище.
Винаги отговаряй въз основа на предоставените документи. Ако липсва информация в локалния архив, провери в законите."""

model = genai.GenerativeModel('gemini-1.5-flash', system_instruction=instruction)


# 3. ЗАРЕЖДАНЕ НА ГЛОБАЛНАТА БАЗА (ЗАКОНИТЕ)
@st.cache_data
def get_global_knowledge():
    context = ""
    knowledge_dir = "ai_knowledge_base"
    if os.path.exists(knowledge_dir):
        for filename in sorted(os.listdir(knowledge_dir)):
            with open(os.path.join(knowledge_dir, filename), 'r', encoding='utf-8') as f:
                context += f"ИЗТОЧНИК {filename}:\n{f.read()}\n\n"
    return context


# 4. ИНТЕРФЕЙС
st.set_page_config(page_title="Chitalishe AI Pro", page_icon="🏛️", layout="wide")

# --- СТРАНИЧНА ЛЕНТА (УПРАВЛЕНИЕ НА АРХИВА) ---
st.sidebar.title("🔐 Личен архив на Читалището")
st.sidebar.write("Тук качвате документите, които са специфични само за вашата организация.")

uploaded_files = st.sidebar.file_uploader(
    "Качете Устав, договори или стари протоколи (PDF/TXT):",
    type=['pdf', 'txt'],
    accept_multiple_files=True
)

local_context = ""
if uploaded_files:
    st.sidebar.success(f"Заредени са {len(uploaded_files)} лични документа.")
    for uploaded_file in uploaded_files:
        if uploaded_file.name.endswith('.pdf'):
            local_context += f"\nДОКУМЕНТ ОТ ВАШИЯ АРХИВ ({uploaded_file.name}):\n" + extract_text_from_pdf(
                uploaded_file)
        else:
            local_context += f"\nДОКУМЕНТ ОТ ВАШИЯ АРХИВ ({uploaded_file.name}):\n" + str(uploaded_file.read(), "utf-8")

# --- ИЗБОР НА РЕЖИМ ---
st.sidebar.divider()
mode = st.sidebar.radio("Действие:", ["⚖️ Консултация и Търсене", "📝 Създаване на протокол (Аудио/Текст)"])

# --- ОСНОВЕН ЕКРАН ---
st.title("🏛️ Читалищен Секретар AI - Професионална версия")

if mode == "⚖️ Консултация и Търсене":
    st.info("ИИ анализира едновременно законите и вашите качени документи.")
    user_input = st.chat_input("Напр. 'Какво казва нашият Устав за избор на председател?'")

    if user_input:
        with st.chat_message("user"): st.markdown(user_input)
        with st.chat_message("assistant"):
            with st.spinner("Проверявам в архивите..."):
                global_kb = get_global_knowledge()
                # Комбинираме всичко: Глобални закони + Локални документи + Въпрос
                full_prompt = f"ГЛОБАЛНИ ЗАКОНИ:\n{global_kb}\n\nЛОКАЛЕН АРХИВ НА ЧИТАЛИЩЕТО:\n{local_context}\n\nВЪПРОС: {user_input}"

                response = model.generate_content(full_prompt)
                st.markdown(response.text)

                # Опция за изтегляне на отговора
                docx = create_docx(response.text)
                st.download_button("📥 Изтегли като Word", data=docx, file_name="consultation.docx")

else:
    # РЕЖИМ ПРОТОКОЛИСТ (С добавено знание от качените документи)
    st.subheader("Генератор на протоколи")
    audio_file = st.file_uploader("Качете запис:", type=['mp3', 'wav', 'm4a'])
    text_input = st.text_area("Или поставете текст тук:", height=150)

    if st.button("Генерирай официален документ"):
        with st.chat_message("assistant"):
            with st.spinner("Работя по документа..."):
                input_data = [
                    f"Използвай този личен архив за контекст:\n{local_context}\n\nНаправи протокол от това събрание:",
                    audio_file if audio_file else text_input]
                response = model.generate_content(input_data)
                st.markdown(response.text)
                docx = create_docx(response.text)
                st.download_button("📥 Изтегли готовия файл", data=docx, file_name="protocol_pro.docx")