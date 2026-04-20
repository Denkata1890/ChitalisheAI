import streamlit as st
import google.generativeai as genai
import os
import warnings


warnings.filterwarnings("ignore")



API_KEY = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('models/gemini-2.5-flash')


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


st.set_page_config(page_title="ИИ Читалищен Секретар", page_icon="🏛️")

st.title("🏛️ ИИ Асистент 'Читалищен Секретар'")
st.subheader("Правен консултант по ЗНЧ и администрация")


user_input = st.text_input("Задайте вашия въпрос към закона:",
                           placeholder="Напр. Колко души е кворумът за Общо събрание?")

if st.button("Провери в закона"):
    if user_input:
        with st.spinner("Проверявам документите..."):
            try:
                context = get_knowledge_base()
                prompt = f"Използвай този контекст: {context}\n\nВъпрос: {user_input}\n\nОтговори професионално и цитирай членове."

                response = model.generate_content(prompt)

                st.markdown("### 📄 Отговор:")
                st.write(response.text)
                st.info("Забележка: Винаги проверявайте официалния текст на закона в Държавен вестник.")
            except Exception as e:
                st.error(f"Възникна грешка: {e}")
    else:
        st.warning("Моля, въведете въпрос.")


st.sidebar.title("За приложението")
st.sidebar.info("Този проект е разработен в помощ на народните читалища в България")