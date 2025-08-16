import requests
import time
import streamlit as st
from config import TTL

def get_usd_to_brl():
    try:
        r = requests.get("https://economia.awesomeapi.com.br/json/last/USD-BRL")
        return float(r.json()["USDBRL"]["bid"])
    except:
        return 5.0

def buscar_detalhes_com_lotes(identificadores, tamanho_lote=75, mostrar_progresso=True):
    todos_detalhes = []
    lotes = [identificadores[i:i + tamanho_lote] for i in range(0, len(identificadores), tamanho_lote)]

    progresso = st.progress(0, text="Buscando detalhes das cartas...") if mostrar_progresso else None

    for i, lote in enumerate(lotes):
        url = "https://api.scryfall.com/cards/collection"
        r = requests.post(url, json={"identifiers": lote})
        if r.status_code == 200:
            todos_detalhes.extend(r.json()["data"])
        if mostrar_progresso:
            progresso.progress((i + 1) / len(lotes))
        time.sleep(0.5)

    if mostrar_progresso:
        progresso.empty()

    return todos_detalhes
