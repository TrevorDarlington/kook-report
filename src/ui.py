"""Shared look and feel: one stylesheet and a few HTML helpers for all pages."""

import streamlit as st

RATING_COLORS = {"Go": "#0E9F6E", "Maybe": "#D98E04", "Don't Go": "#D14B4B"}
RATING_TINTS = {"Go": "#E3F6EE", "Maybe": "#FBF1DA", "Don't Go": "#FBE6E6"}

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@500;600;700;800&display=swap');

:root {
  --ink: #0B2533; --muted: #5B7482; --line: #E1ECEF; --deep: #06324A; --teal: #0B7285;
  --display: 'Outfit', -apple-system, 'Segoe UI', sans-serif;
}
[data-testid="stMainBlockContainer"] {max-width: 640px; padding: 3.5rem 1rem 3rem 1rem;}
[data-testid="stHeader"] {background: rgba(244, 250, 251, 0.92); backdrop-filter: blur(6px);}
h1, h2, h3 {font-family: var(--display); letter-spacing: -0.01em; color: var(--ink);}

.hero {background: linear-gradient(150deg, #06324A 0%, #0B7285 70%, #18A0A6 100%);
       color: white; border-radius: 20px; padding: 22px; margin-bottom: 14px;
       position: relative; overflow: hidden; box-shadow: 0 8px 24px rgba(6, 50, 74, 0.18);}
.hero .brand {font-family: var(--display); font-weight: 700; font-size: 0.8rem;
              letter-spacing: 0.16em; text-transform: uppercase; opacity: 0.8;}
.hero .question {font-size: 0.95rem; opacity: 0.85; margin-top: 14px;}
.hero .answer {font-family: var(--display); font-weight: 800; font-size: 2.3rem; line-height: 1.1; margin-top: 2px;}
.hero .sub {font-size: 1rem; opacity: 0.92; margin-top: 8px; line-height: 1.4;}
.hero.small .answer {font-size: 1.7rem; margin-top: 10px;}

.section {font-family: var(--display); font-weight: 700; font-size: 0.78rem; letter-spacing: 0.12em;
          text-transform: uppercase; color: var(--muted); margin: 20px 2px 8px 2px;}

.card {background: white; border: 1px solid var(--line); border-radius: 16px; padding: 16px;
       margin-bottom: 12px; box-shadow: 0 2px 8px rgba(11, 37, 51, 0.05);}
.card.top {border: 2px solid var(--c);}
.card-head {display: flex; justify-content: space-between; align-items: center; gap: 10px;}
.beach {font-family: var(--display); font-weight: 700; font-size: 1.2rem; color: var(--ink);}
.tag {font-size: 0.7rem; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase;
      color: var(--c); margin-bottom: 2px;}
.pill {background: var(--c); color: white; font-family: var(--display); font-weight: 700;
       font-size: 0.95rem; padding: 5px 14px; border-radius: 999px; white-space: nowrap;}
.reason {font-size: 1.02rem; line-height: 1.4; color: var(--ink); margin: 10px 0 12px 0;}

.timeline {display: flex; gap: 3px;}
.timeline span {flex: 1; height: 8px; border-radius: 4px;}
.timeline-labels {display: flex; justify-content: space-between; font-size: 0.72rem;
                  color: var(--muted); margin-top: 4px;}

.stats {display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; margin-top: 12px;
        padding-top: 12px; border-top: 1px solid var(--line);}
.stat .label {font-size: 0.64rem; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; color: var(--muted);}
.stat .value {font-family: var(--display); font-weight: 700; font-size: 1.05rem; color: var(--ink); line-height: 1.25;}
.stat .note {font-size: 0.74rem; color: var(--muted);}

.outlook {width: 100%; border-collapse: separate; border-spacing: 0 6px;}
.outlook th {font-size: 0.72rem; font-weight: 700; color: var(--muted); text-align: center; padding: 0 2px;}
.outlook td {padding: 0 2px; text-align: center;}
.outlook td.name {text-align: left; font-weight: 600; font-size: 0.88rem; color: var(--ink); padding-left: 0;}
.chip {display: block; border-radius: 8px; padding: 6px 0; font-size: 0.76rem; font-weight: 700;}

.legend {display: flex; gap: 14px; font-size: 0.76rem; color: var(--muted); margin: 2px 2px 0 2px;}
.legend i {display: inline-block; width: 9px; height: 9px; border-radius: 3px; margin-right: 5px;}

.fineprint {font-size: 0.8rem; color: var(--muted); line-height: 1.45; margin-top: 18px;}

.stats.three {grid-template-columns: repeat(3, 1fr); margin-top: 0; padding-top: 0; border-top: none;}
.stats.three .value {font-size: 1.5rem;}

[data-testid="stPageLink"] a {border-radius: 999px; padding: 4px 14px; border: 1px solid var(--line); background: white;}
[data-testid="stPageLink"] p {font-weight: 600; font-size: 0.9rem;}
</style>
"""

def inject_css():
    st.markdown(CSS, unsafe_allow_html=True)


def hero(answer, sub="", question="", small=False):
    """The banner at the top of every page."""
    parts = ['<div class="brand">Kook Report</div>']
    if question:
        parts.append(f'<div class="question">{question}</div>')
    parts.append(f'<div class="answer">{answer}</div>')
    if sub:
        parts.append(f'<div class="sub">{sub}</div>')
    kind = "hero small" if small else "hero"
    st.html(f'<div class="{kind}">{"".join(parts)}</div>')


def section(title):
    st.html(f'<div class="section">{title}</div>')
