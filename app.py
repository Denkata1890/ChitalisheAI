import streamlit as st
import io
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# --- 1. СИСТЕМА ЗА ВХОД (SECRETS) ---
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


# --- 2. ФУНКЦИИ ЗА GOOGLE DRIVE ---
def get_drive_service():
    info = st.secrets["gcp_service_account"]
    credentials = service_account.Credentials.from_service_account_info(info)
    scoped_credentials = credentials.with_scopes(['https://www.googleapis.com/auth/drive'])
    return build('drive', 'v3', credentials=scoped_credentials)


def get_or_create_folder(folder_name):
    service = get_drive_service()
    # Търсим папката в целия Drive (не само в основната папка)
    query = f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    items = results.get('files', [])

    if not items:
        file_metadata = {'name': folder_name, 'mimeType': 'application/vnd.google-apps.folder'}
        folder = service.files().create(body=file_metadata, fields='id').execute()
        return folder.get('id')
    return items[0]['id']


def upload_to_drive(file_content, file_name, folder_id):
    service = get_drive_service()
    file_metadata = {'name': file_name, 'parents': [folder_id]}
    media = MediaIoBaseUpload(io.BytesIO(file_content), mimetype='application/octet-stream')
    service.files().create(body=file_metadata, media_body=media, fields='id').execute()


# --- 3. ИНТЕРФЕЙС НА ПРИЛОЖЕНИЕТО ---
st.sidebar.write(f"👤 Вписани сте като: **{st.session_state['username']}**")
if st.sidebar.button("Изход"):
    st.session_state["authenticated"] = False
    st.rerun()

st.title("🏛️ Дигитален Читалищен Секретар")
st.write(f"Добре дошли, {st.session_state['username']}! Качете документи за съхранение и анализ.")

# Компонент за качване на файлове
uploaded_file = st.file_uploader("Изберете PDF или текстов документ", type=['pdf', 'txt', 'docx'])

if uploaded_file is not None:
    # 1. Специфична папка за потребителя
    user_folder_name = st.session_state['username']

    with st.spinner("💾 Качване в облачния архив..."):
        try:
            # Намираме или създаваме папка за читалището
            folder_id = get_or_create_folder(user_folder_name)

            # Качваме файла
            file_bytes = uploaded_file.getvalue()
            upload_to_drive(file_bytes, uploaded_file.name, folder_id)

            st.success(f"✅ Файлът '{uploaded_file.name}' е запазен успешно в Google Drive!")
        except Exception as e:
            st.error(f"❌ Грешка при качване: {e}")

# Тук по-късно ще добавим и връзката с Gemini за анализ на вече качените файлове