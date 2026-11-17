import streamlit as st

from src import ui

st.set_page_config(page_title="Kook Report", layout="centered")
ui.inject_css()

pages = [
    st.Page("views/forecast.py", title="Forecast", default=True),
    st.Page("views/scorecard.py", title="Accuracy", url_path="accuracy"),
    st.Page("views/about.py", title="About", url_path="about"),
]
current = st.navigation(pages, position="hidden")
with st.container(horizontal=True, gap="small"):
    for page in pages:
        st.page_link(page)
current.run()
