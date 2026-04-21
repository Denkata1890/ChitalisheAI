import streamlit as st
import google.generativeai as genai
import os
from docx import Document
from io import BytesIO
import PyPDF2

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io


# 1. ФУНКЦИЯ ЗА СВЪРЗВАНЕ С DRIVE
def get_drive_service():
    # Използваме "тайните", които току-що сложи в Secrets
    info = st.secrets["gcp_service_account"]
    credentials = service_account.Credentials.from_service_account_info(info)
    scoped_credentials = credentials.with_scopes(['https://www.googleapis.com/auth/drive'])
    return build('drive', 'v3', credentials=scoped_credentials)


# 2. ФУНКЦИЯ ЗА СЪЗДАВАНЕ НА ПАПКА (Ако не съществува)
def get_or_create_folder(folder_name):
    service = get_drive_service()
    # Търсим дали вече има папка с такова име
    query = f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    items = results.get('files', [])

    if not items:
        # Ако няма, я създаваме
        file_metadata = {'name': folder_name, 'mimeType': 'application/vnd.google-apps.folder'}
        folder = service.files().create(body=file_metadata, fields='id').execute()
        return folder.get('id')
    return items[0]['id']


# 3. ФУНКЦИЯ ЗА КАЧВАНЕ НА ФАЙЛ
def upload_to_drive(file_content, file_name, folder_id):
    service = get_drive_service()
    file_metadata = {'name': file_name, 'parents': [folder_id]}
    media = MediaIoBaseUpload(io.BytesIO(file_content), mimetype='application/octet-stream')
    service.files().create(body=file_metadata, media_body=media, fields='id').execute()
# 1. ТУК КАЗВАМЕ НА ПРОГРАМАТА ДА ВЗЕМЕ ПАРОЛИТЕ ОТ "СЕЙФА"
try:
    # Опитваме се да вземем списъка с потребители от Secrets
    USERS = st.secrets["users"]
except:
    # Ако тестваме локално на компютъра и нямаме сейф, ползваме тази парола по подразбиране
    USERS = {"admin": "admin123"}


# 2. ФУНКЦИЯ ЗА ПРОВЕРКА НА ВХОДА
def check_password():
    # Проверяваме дали в "паметта" на браузъра вече пише, че сме вписани
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    # Ако вече сме се логнали успешно, просто продължаваме
    if st.session_state["authenticated"]:
        return True

    # АКО НЕ СМЕ ЛОГНАТИ: Показваме формата за вход
    st.title("🔐 Вход в Chitalishe AI Pro")
    user = st.text_input("Потребителско име")
    password = st.text_input("Парола", type="password")

    if st.button("Влизане"):
        # Проверяваме дали името съществува в USERS и дали паролата съвпада
        if user in USERS and USERS[user] == password:
            st.session_state["authenticated"] = True  # Запомни, че сме влезли
            st.session_state["username"] = user  # Запомни кой влезе
            st.rerun()  # Рестартирай страницата, за да се появи менюто
        else:
            st.error("❌ Грешно потребителско име или парола")
    return False


# 3. КЛЮЧОВИЯТ МОМЕНТ
# Ако функцията върне "False" (т.е. няма успех с паролата), спри целия код дотук!
if not check_password():
    st.stop()


def check_password():
    """Връща True, ако потребителят е въвел правилна парола."""
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if st.session_state["authenticated"]:
        return True

    # Екран за вход
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


# Спираме изпълнението на останалия код, ако не е вписан
if not check_password():
    st.stop()

# Постави това след проверката на паролата
if st.session_state["username"] == "admin":
    st.sidebar.warning("🛠️ Влезли сте като Администратор. Имате пълен достъп.")
else:
    st.sidebar.info(f"🏛️ Добре дошли, НЧ 'Светлина - 1861г.'")

# Създаваме уникално име на папката за съответния потребител
user_folder = f"data_{st.session_state['username']}"
# --- ОТТУК НАТАТЪК СЛЕДВА ОСТАНАЛИЯТ ТИ КОД ---
st.sidebar.write(f"👤 Вписани сте като: **{st.session_state['username']}**")
if st.sidebar.button("Изход"):
    st.session_state["authenticated"] = False
    st.rerun()

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