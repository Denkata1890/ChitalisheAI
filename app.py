import streamlit as st
import io
import google.generativeai as genai
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import PyPDF2

# ==========================================
# 1. ОСНОВНИ НАСТРОЙКИ (Сложи твоето ID тук!)
# ==========================================
PARENT_FOLDER_ID = "https://drive.google.com/drive/folders/1nGBrDKG14XUtA70J4j2ZpSEFxc5FGsJE"

# Настройка на Gemini
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    st.error(f"Грешка при настройка на Gemini: {e}")


# ==========================================
# 2. ФУНКЦИИ ЗА GOOGLE DRIVE
# ==========================================
def get_drive_service():
    info = st.secrets["gcp_service_account"]
    credentials = service_account.Credentials.from_service_account_info(info)
    scoped_credentials = credentials.with_scopes(['https://www.googleapis.com/auth/drive'])
    return build('drive', 'v3', credentials=scoped_credentials)


def get_or_create_folder(folder_name):
    service = get_drive_service()
    # Търсим папката на читалището ВЪТРЕ в основната папка
    query = f"name = '{folder_name}' and '{PARENT_FOLDER_ID}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    items = results.get('files', [])

    if not items:
        # Създаваме нова подпапка с родител PARENT_FOLDER_ID
        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [PARENT_FOLDER_ID]
        }
        folder = service.files().create(body=file_metadata, fields='id').execute()
        return folder.get('id')
    return items[0]['id']


def upload_to_drive(file_content, file_name, folder_id):
    service = get_drive_service()
    file_metadata = {'name': file_name, 'parents': [folder_id]}
    media = MediaIoBaseUpload(io.BytesIO(file_content), mimetype='application/octet-stream')
    service.files().create(body=file_metadata, media_body=media, fields='id').execute()


# ==========================================
# 3. СИСТЕМА ЗА ВХОД
# ==========================================
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if st.session_state["authenticated"]:
        return True

    st.title("🔐 Вход в Chitalishe AI Pro")
    user_input = st.text_input("Потребителско име")
    pass_input = st.text_input("Парола", type="password")

    if st.button("Влизане"):
        if "users" in st.secrets and user_input in st.secrets["users"] and st.secrets["users"][
            user_input] == pass_input:
            st.session_state["authenticated"] = True
            st.session_state["username"] = user_input
            st.rerun()
        else:
            st.error("❌ Грешно потребителско име или парола")
    return False


# Спираме изпълнението тук, ако не е логнат
if not check_password():
    st.stop()

# ==========================================
# 4. ГЛАВЕН ИНТЕРФЕЙС (Изпълнява се само след Login)
# ==========================================
st.sidebar.title(f"👤 {st.session_state['username']}")
if st.sidebar.button("Изход"):
    st.session_state["authenticated"] = False
    st.rerun()

st.title("🏛️ Дигитален Читалищен Секретар")
st.write("Качете документ, за да го анализираме и запишем в облака.")

uploaded_file = st.file_uploader("Изберете PDF или TXT файл", type=['pdf', 'txt'])

if uploaded_file is not None:
    # ИНДИКАТОР ЗА ДЕБЪГ (Ще видиш това веднага при качване)
    st.info(f"🔎 Обработка на файл: {uploaded_file.name}")

    user_folder_name = st.session_state['username']

    # ЛОГИКА ЗА КАЧВАНЕ В DRIVE
    if "last_uploaded" not in st.session_state or st.session_state.last_uploaded != uploaded_file.name:
        with st.spinner("💾 Записване в Google Drive..."):
            try:
                # Вземаме ID на папката
                folder_id = get_or_create_folder(user_folder_name)
                # Качваме съдържанието
                file_bytes = uploaded_file.getvalue()
                upload_to_drive(file_bytes, uploaded_file.name, folder_id)

                st.session_state.last_uploaded = uploaded_file.name
                st.success(f"✅ Файлът е архивиран в Drive (Folder ID: {folder_id})")
            except Exception as e:
                st.error(f"❌ Грешка при качване в Drive: {e}")

    # ЛОГИКА ЗА GEMINI (АНАЛИЗ)
    try:
        if uploaded_file.type == "application/pdf":
            reader = PyPDF2.PdfReader(uploaded_file)
            text_content = "".join([page.extract_text() for page in reader.pages])
        else:
            text_content = uploaded_file.read().decode("utf-8")

        st.divider()
        user_question = st.text_input("❓ Задайте въпрос към документа:")

        if user_question:
            with st.spinner("🤖 Мисля..."):
                prompt = f"Ти си читалищен експерт. На база на този текст: {text_content}\n\nОтговори на въпроса: {user_question}"
                response = model.generate_content(prompt)
                st.markdown("### 🤖 Отговор:")
                st.write(response.text)
    except Exception as e:
        st.error(f"❌ Грешка при четене на файла: {e}")