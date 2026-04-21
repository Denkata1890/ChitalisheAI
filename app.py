import streamlit as st
import io
import google.generativeai as genai
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import PyPDF2

# ==========================================
# 1. ТВОЕТО НОВО ID НА ПОДПАПКАТА
# ==========================================
# Сложи тук ID-то на папката 'nch_svetlina_shipka', която създаде ръчно
PARENT_FOLDER_ID = "1w08JtXDo4Si3zNXrdP_D3iXrgCTkZHJg"

# Настройка на Gemini
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    st.error(f"Грешка при Gemini: {e}")

# ==========================================
# 2. ФУНКЦИИ ЗА GOOGLE DRIVE (ОПТИМИЗИРАНИ)
# ==========================================
def upload_to_drive(file_content, file_name, folder_id):
    service = get_drive_service()

    # 1. Подготвяме метаданните
    file_metadata = {
        'name': file_name,
        'parents': [folder_id]
    }

    # 2. Използваме директно качване (без resumable), за да избегнем квотната проверка при малки файлове
    media = MediaIoBaseUpload(
        io.BytesIO(file_content),
        mimetype='application/octet-stream',
        chunksize=1024 * 1024,  # 1MB парчета
        resumable=False  # ВАЖНО: Пробвай с False
    )

    try:
        # 3. Опит за качване
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id',
            supportsAllDrives=True
        ).execute()
        return file.get('id')

    except Exception as e:
        # Ако пак даде Quota error, това е заради собствеността.
        # Единственият изход е да ползваш "Shared Drive" (ако имаш Workspace)
        # или да качваш файла като "Google Doc" тип, който понякога не заема място
        raise e

# ==========================================
# 3. СИСТЕМА ЗА ВХОД
# ==========================================
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    if st.session_state["authenticated"]:
        return True
    st.title("🔐 Вход")
    user_input = st.text_input("Потребителско име")
    pass_input = st.text_input("Парола", type="password")
    if st.button("Влизане"):
        if "users" in st.secrets and user_input in st.secrets["users"] and st.secrets["users"][user_input] == pass_input:
            st.session_state["authenticated"] = True
            st.session_state["username"] = user_input
            st.rerun()
        else:
            st.error("❌ Грешка")
    return False

if not check_password():
    st.stop()

# ==========================================
# 4. ИНТЕРФЕЙС И КАЧВАНЕ
# ==========================================
st.title("🏛️ Дигитален Секретар")

uploaded_file = st.file_uploader("Изберете файл", type=['pdf', 'txt'])

if uploaded_file is not None:
    # Защита от повторно качване
    if "last_uploaded" not in st.session_state or st.session_state.last_uploaded != uploaded_file.name:
        with st.spinner("💾 Изпращане към Вашия Google Drive..."):
            try:
                file_bytes = uploaded_file.getvalue()
                # КАЧВАМЕ ДИРЕКТНО В PARENT_FOLDER_ID
                f_id = upload_to_drive(file_bytes, uploaded_file.name, PARENT_FOLDER_ID)
                st.session_state.last_uploaded = uploaded_file.name
                st.success(f"✅ Готово! Файлът е записан успешно.")
            except Exception as e:
                st.error(f"❌ Проблем при запис: {e}")

    # GEMINI АНАЛИЗ
    try:
        if uploaded_file.type == "application/pdf":
            reader = PyPDF2.PdfReader(uploaded_file)
            text_content = "".join([page.extract_text() for page in reader.pages])
        else:
            text_content = uploaded_file.read().decode("utf-8")

        st.divider()
        user_question = st.text_input("❓ Попитайте нещо за документа:")
        if user_question:
            with st.spinner("🤖 Анализирам..."):
                response = model.generate_content(f"Текст: {text_content}\nВъпрос: {user_question}")
                st.write(response.text)
    except Exception as e:
        st.error(f"Грешка при четене: {e}")