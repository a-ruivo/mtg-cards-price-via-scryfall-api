import streamlit as st

CSV_PATH = "cartas_magic_detalhadas.csv"
REPO = "a-ruivo/mtg-cards-price-via-scryfall-api"
GITHUB_TOKEN = st.secrets["github_token"]
TTL = 86400  # 24 horas
