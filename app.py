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
    model_name='gemini-1.5-flash',
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

# ... (началото на кода остава същото) ...

if mode == "⚖️ Правна консултация":
    st.subheader("Търсене в законите и администрацията")
    user_input = st.chat_input("Напр. Какъв е мандатът на Настоятелството?")
else:
    st.subheader("Генератор на протоколи от събрания")

    # СЪЗДАВАМЕ ДВА ТАБА - ЕДИН ЗА ТЕКСТ И ЕДИН ЗА АУДИО
    tab1, tab2 = st.tabs(["📝 Суров текст", "🎙️ Аудио запис"])

    with tab1:
        text_input = st.text_area("Поставете транскрипция тук:", height=200)

    with tab2:
        audio_file = st.file_uploader("Качете аудио файл от събранието (mp3, wav, m4a):", type=['mp3', 'wav', 'm4a'])
        if audio_file:
            st.audio(audio_file)

    if st.button("Генерирай протокол"):
        if mode == "📝 Дигитален протоколист":
            with st.chat_message("assistant"):
                with st.spinner("Анализирам срещата..."):
                    try:
                        if audio_file:
                            # Изпращаме аудиото директно към Gemini
                            prompt = "Това е аудио запис от събрание на читалище. Моля, направи официален протокол."
                            response = model.generate_content([prompt, audio_file])
                        else:
                            # Ползваме суровия текст
                            prompt = f"Направи официален протокол от този текст:\n\n{text_input}"
                            response = model.generate_content(prompt)

                        answer = response.text
                        st.markdown(answer)

                        # Бутон за Word
                        docx_file = create_docx(answer)
                        st.download_button("📥 Изтегли Протокола", data=docx_file, file_name="protocol.docx")
                    except Exception as e:
                        st.error(f"Грешка: {e}")