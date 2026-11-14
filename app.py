import streamlit as st

st.set_page_config(page_title="Kook Report", layout="centered")

pages = [
    st.Page("views/forecast.py", title="Forecast", default=True),
    st.Page("views/scorecard.py", title="Accuracy", url_path="accuracy"),
    st.Page("views/about.py", title="About", url_path="about"),
]
st.navigation(pages, position="top").run()
