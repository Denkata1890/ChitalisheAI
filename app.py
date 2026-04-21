import streamlit as st
import io
import google.generativeai as genai
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import PyPDF2


PARENT_FOLDER_ID = "https://drive.google.com/drive/folders/1nGBrDKG14XUtA70J4j2ZpSEFxc5FGsJE"
# --- 1. НАСТРОЙКА НА GEMINI ---
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    st.error("Грешка при конфигуриране на Gemini API.")

# --- 2. СИСТЕМА ЗА ВХОД (SECRETS) ---
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


# --- 3. ФУНКЦИИ ЗА GOOGLE DRIVE ---
def get_drive_service():
    info = st.secrets["gcp_service_account"]
    credentials = service_account.Credentials.from_service_account_info(info)
    scoped_credentials = credentials.with_scopes(['https://www.googleapis.com/auth/drive'])
    return build('drive', 'v3', credentials=scoped_credentials)


def get_or_create_folder(folder_name):
    service = get_drive_service()

    # Търсим дали папката на читалището вече съществува вътре в твоята основна папка
    query = f"name = '{folder_name}' and '{PARENT_FOLDER_ID}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    items = results.get('files', [])

    if not items:
        # СЪЗДАВАНЕ: Важно е да подадем PARENT_FOLDER_ID като родител
        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [PARENT_FOLDER_ID]
        }
        folder = service.files().create(body=file_metadata, fields='id').execute()
        folder_id = folder.get('id')
        st.write(f"📁 Създадена нова папка с ID: {folder_id}")  # Това ще се появи в сайта
        return folder_id

    return items[0]['id']


def upload_to_drive(file_content, file_name, folder_id):
    service = get_drive_service()
    file_metadata = {
        'name': file_name,
        'parents': [folder_id]
    }
    media = MediaIoBaseUpload(io.BytesIO(file_content), mimetype='application/octet-stream')
    uploaded_file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    st.write(f"🚀 Файлът е качен успешно с ID: {uploaded_file.get('id')}")

# --- 4. ФУНКЦИЯ ЗА ЧЕТЕНЕ НА PDF ---
def read_pdf(file):
    pdf_reader = PyPDF2.PdfReader(file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text


# --- 5. ИНТЕРФЕЙС НА ПРИЛОЖЕНИЕТО ---
st.sidebar.write(f"👤 Потребител: **{st.session_state['username']}**")
if st.sidebar.button("Изход"):
    st.session_state["authenticated"] = False
    st.rerun()

st.title("🏛️ Дигитален Читалищен Секретар")
st.info("Качете документ (Устав, Протокол, Отчет), за да го запазите в облака и да зададете въпроси към него.")

uploaded_file = st.file_uploader("Изберете файл", type=['pdf', 'txt'])

if uploaded_file is not None:
    st.write("🔎 Файлът е засечен от системата...")  # Това трябва да се появи веднага

    user_folder_name = st.session_state['username']

    # ПРОВЕРКА: Вече качен ли е този файл в тази сесия?
    if "last_uploaded" not in st.session_state or st.session_state.last_uploaded != uploaded_file.name:
        with st.spinner("💾 Опит за качване в Google Drive..."):
            try:
                # 1. Свързване
                folder_id = get_or_create_folder(user_folder_name)
                st.write(f"📂 Работим в папка с ID: {folder_id}")

                # 2. Качване
                file_bytes = uploaded_file.getvalue()
                upload_to_drive(file_bytes, uploaded_file.name, folder_id)

                # 3. Маркираме като качен
                st.session_state.last_uploaded = uploaded_file.name
                st.success(f"✅ УСПЕХ: {uploaded_file.name} е в облака!")
            except Exception as e:
                st.error(f"❌ ГРЕШКА ПРИ КАЧВАНЕ: {e}")
    else:
        st.info("ℹ️ Този файл вече беше качен успешно.")

    # СТЪПКА Б: ОБРАБОТКА И АНАЛИЗ С GEMINI
    with st.spinner("🧠 ИИ анализира документа..."):
        if uploaded_file.type == "application/pdf":
            text_content = read_pdf(uploaded_file)
        else:
            text_content = uploaded_file.read().decode("utf-8")

        st.success("Документът е готов за въпроси!")

        user_question = st.text_input("Какво искате да разберете от този документ?")

        if user_question:
            prompt = f"""
            Ти си експерт по работата на народните читалища в България. 
            Използвай следния текст от документ, за да отговориш на въпроса.
            Текст: {text_content}
            Въпрос: {user_question}
            """
            response = model.generate_content(prompt)
            st.markdown("### 🤖 Отговор:")
            st.write(response.text)

st.write("---")
st.write("DEBUG: Програмата стигна до края на файла.")