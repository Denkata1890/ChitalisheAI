import streamlit as st
import google.generativeai as genai
import PyPDF2
import io

# ==========================================
# 1. НАСТРОЙКИ
# ==========================================
st.set_page_config(page_title="Chitalishe AI Pro", page_icon="🏛️")

# Настройка на Gemini
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    st.error("Липсва Gemini API Key в Secrets!")


# ==========================================
# 2. СИСТЕМА ЗА ВХОД
# ==========================================
def check_password():
    if st.session_state.get("authenticated"):
        return True

    st.title("🏛️ Читалищен Секретар AI")
    st.subheader("Моля, влезте в системата")

    user_input = st.text_input("Потребителско име")
    pass_input = st.text_input("Парола", type="password")

    if st.button("Влизане"):
        if "users" in st.secrets and user_input in st.secrets["users"]:
            if st.secrets["users"][user_input] == pass_input:
                st.session_state["authenticated"] = True
                st.session_state["username"] = user_input
                st.rerun()
            else:
                st.error("❌ Грешна парола")
        else:
            st.error("❌ Потребителят не съществува")
    return False


if not check_password():
    st.stop()

# ==========================================
# 3. ГЛАВЕН ИНТЕРФЕЙС
# ==========================================
st.sidebar.title(f"👤 {st.session_state['username']}")
if st.sidebar.button("Изход"):
    st.session_state["authenticated"] = False
    st.rerun()

st.title("🏛️ Дигитален Читалищен Секретар")
st.markdown("---")

# Списък за "Библиотека" (съхранява се в сесията на приложението)
if "library" not in st.session_state:
    st.session_state["library"] = []

# Качване на файл
uploaded_file = st.file_uploader("Качете документ (PDF или TXT)", type=['pdf', 'txt'])

if uploaded_file is not None:
    # Проверка дали файлът вече е в библиотеката
    file_exists = any(item['name'] == uploaded_file.name for item in st.session_state.library)

    if not file_exists:
        with st.spinner("📦 Обработка и архивиране..."):
            # Извличане на текст
            try:
                if uploaded_file.type == "application/pdf":
                    reader = PyPDF2.PdfReader(uploaded_file)
                    text_content = "".join([page.extract_text() for page in reader.pages])
                else:
                    text_content = uploaded_file.read().decode("utf-8")

                # Добавяне в библиотеката
                st.session_state.library.append({
                    "name": uploaded_file.name,
                    "content": text_content
                })
                st.success(f"✅ Файлът '{uploaded_file.name}' е добавен в библиотеката!")
            except Exception as e:
                st.error(f"Грешка при четене: {e}")

    # Избор на файл за работа от библиотеката
    current_file = next((item for item in st.session_state.library if item['name'] == uploaded_file.name), None)

    if current_file:
        st.info(f"📄 Активен документ: **{current_file['name']}**")

        # Чат с документа
        st.subheader("🤖 Попитайте AI за този документ")
        user_question = st.text_input("Въведете въпрос (напр. 'Направи резюме' или 'Кога е крайният срок?'):")

        if user_question:
            with st.spinner("🧠 Мисля..."):
                try:
                    prompt = f"""
                    Ти си експерт по читалищна дейност и администрация. 
                    Базирай се на следния текст: {current_file['content']}
                    Отговори на въпроса: {user_question}
                    """
                    response = model.generate_content(prompt)
                    st.markdown("### 🤖 Отговор:")
                    st.write(response.text)
                except Exception as e:
                    st.error(f"Грешка при Gemini: {e}")

# ==========================================
# 4. БИБЛИОТЕКА (SIDEBAR)
# ==========================================
if st.session_state.library:
    st.sidebar.markdown("---")
    st.sidebar.subheader("📚 Вашата библиотека")
    for doc in st.session_state.library:
        st.sidebar.write(f"• {doc['name']}")