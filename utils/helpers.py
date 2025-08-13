import streamlit as st
import pandas as pd
from config import TTL

@st.cache_data(ttl=TTL)
def dividir_em_lotes(lista, tamanho):
    for i in range(0, len(lista), tamanho):
        yield lista[i:i + tamanho]

@st.cache_data(ttl=TTL)
def gerar_icones(valores, mapa):
    icones = []
    for v in str(valores).split(","):
        v = v.strip()
        if v in mapa:
            icones.append(f'<img src="{mapa[v]}" width="25">')
        else:
            icones.append(v)
    return " ".join(icones)

def preparar_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df = df.dropna(subset=["colecao", "numero"])
    df["colecao"] = df["colecao"].astype(str).str.lower()
    df["numero"] = df["numero"].astype(str)
    df["padrao"] = pd.to_numeric(df["padrao"], errors="coerce").fillna(1)
    df["foil"] = pd.to_numeric(df["foil"], errors="coerce").fillna(0)


    df = df.groupby(["colecao", "numero"], as_index=False).agg({
        "padrao": "sum",
        "foil": "sum",
        **{col: "first" for col in df.columns if col not in ["colecao", "numero", "padrao", "foil"]}
    })

    return df

def limpar_e_enriquecer_dataframe(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    # Corrigir coluna "cores" com base no tipo
    df["cores"] = df.apply(
        lambda row: "L" if "Land" in str(row["tipo"]) else (
            "C" if pd.isna(row["cores"]) or str(row["cores"]).strip() == "" else row["cores"]
        ),
        axis=1
    )

    # Conversões e limpeza
    df = df.astype(str)
    df["mana_cost"] = df["mana_cost"].astype(str)
    df["mana_cost"] = df["mana_cost"].str.replace("nan", "", regex=False)
    df["mana_cost"] = df["mana_cost"].str.replace("//", "/", regex=False)
    df["mana_cost"] = df["mana_cost"].str.replace("{", "", regex=False)
    df["mana_cost"] = df["mana_cost"].str.replace("}", "", regex=False)

    df["padrao"] = pd.to_numeric(df["padrao"], errors="coerce").fillna(0).replace([float("inf"), float("-inf")], 0).astype(int)
    df["foil"] = pd.to_numeric(df["foil"], errors="coerce").fillna(0).replace([float("inf"), float("-inf")], 0).astype(int)

    df["preco_brl"] = df["preco_brl"].replace("nan", "0").astype(float)
    df["preco_brl_foil"] = df["preco_brl_foil"].replace("nan", "0").astype(float)

    # Valor total
    df["valor_total_brl"] = (
        df["padrao"] * df["preco_brl"] +
        df["foil"] * df["preco_brl_foil"]
    )

    # Mapeamento de coleções
    colecao_map = {
        row["colecao"]: {
            "nome": row["colecao_nome"],
            "icone": row["icone_colecao"]
        }
        for _, row in df.drop_duplicates(subset=["colecao"]).iterrows()
    }

    return df, colecao_map

def get_mana_map() -> dict:
    return {
        "W": "https://svgs.scryfall.io/card-symbols/W.svg",
        "U": "https://svgs.scryfall.io/card-symbols/U.svg",
        "B": "https://svgs.scryfall.io/card-symbols/B.svg",
        "R": "https://svgs.scryfall.io/card-symbols/R.svg",
        "G": "https://svgs.scryfall.io/card-symbols/G.svg",
        "C": "https://svgs.scryfall.io/card-symbols/C.svg",
        "L": "https://svgs.scryfall.io/card-symbols/L.svg",
        "S": "https://svgs.scryfall.io/card-symbols/S.svg",
        "W/U": "https://svgs.scryfall.io/card-symbols/WU.svg",
        "W/B": "https://svgs.scryfall.io/card-symbols/WB.svg",
        "U/B": "https://svgs.scryfall.io/card-symbols/UB.svg",
        "U/R": "https://svgs.scryfall.io/card-symbols/UR.svg",
        "B/R": "https://svgs.scryfall.io/card-symbols/BR.svg",
        "B/G": "https://svgs.scryfall.io/card-symbols/BG.svg",
        "R/G": "https://svgs.scryfall.io/card-symbols/RG.svg",
        "R/W": "https://svgs.scryfall.io/card-symbols/RW.svg",
        "G/W": "https://svgs.scryfall.io/card-symbols/GW.svg",
        "G/U": "https://svgs.scryfall.io/card-symbols/GU.svg",
        "W/P": "https://svgs.scryfall.io/card-symbols/WP.svg",
        "U/P": "https://svgs.scryfall.io/card-symbols/UP.svg",
        "B/P": "https://svgs.scryfall.io/card-symbols/BP.svg",
        "R/P": "https://svgs.scryfall.io/card-symbols/RP.svg",
        "G/P": "https://svgs.scryfall.io/card-symbols/GP.svg",
        "C/P": "https://svgs.scryfall.io/card-symbols/CP.svg",
        "2/W": "https://svgs.scryfall.io/card-symbols/2W.svg",
        "2/U": "https://svgs.scryfall.io/card-symbols/2U.svg",
        "2/B": "https://svgs.scryfall.io/card-symbols/2B.svg",
        "2/R": "https://svgs.scryfall.io/card-symbols/2R.svg",
        "2/G": "https://svgs.scryfall.io/card-symbols/2G.svg",
        "C/W": "https://svgs.scryfall.io/card-symbols/CW.svg",
        "C/U": "https://svgs.scryfall.io/card-symbols/CU.svg",
        "C/B": "https://svgs.scryfall.io/card-symbols/CB.svg",
        "C/R": "https://svgs.scryfall.io/card-symbols/CR.svg",
        "C/G": "https://svgs.scryfall.io/card-symbols/CG.svg",
        "HW": "https://svgs.scryfall.io/card-symbols/HW.svg",
        "HR": "https://svgs.scryfall.io/card-symbols/HR.svg",
        "X": "https://svgs.scryfall.io/card-symbols/X.svg",
        "T": "https://svgs.scryfall.io/card-symbols/T.svg",
        "Q": "https://svgs.scryfall.io/card-symbols/Q.svg",
        "E": "https://svgs.scryfall.io/card-symbols/E.svg",
        "A": "https://svgs.scryfall.io/card-symbols/A.svg",
        "CHAOS": "https://svgs.scryfall.io/card-symbols/CHAOS.svg",
        "PW": "https://svgs.scryfall.io/card-symbols/PW.svg",
    }

def autenticar():
    senha_correta = st.secrets["senha_app"]
    senha_digitada = st.text_input("Enter the password to edit the collection", type="password")
    if senha_digitada == senha_correta:
        st.session_state["autenticado"] = True
    elif senha_digitada:
        st.error("Wrong password.")

def extrair_detalhes_cartas(df: pd.DataFrame, todos_detalhes: list, cotacao: float) -> pd.DataFrame:
    detalhes_dict = {}

    for carta in todos_detalhes:
        preco_usd = float(carta.get("prices", {}).get("usd") or 0)
        preco_foil = float(carta.get("prices", {}).get("usd_foil") or 0)
        preco_brl = round(preco_usd * cotacao, 2)
        preco_brl_foil = round(preco_foil * cotacao, 2)
        faces = carta.get("card_faces", [])
        face1 = faces[0] if faces else carta
        face2 = faces[1] if len(faces) > 1 else {}

        detalhes_dict[(carta["set"], carta["collector_number"])] = {
            "nome": face1.get("name"),
            "mana_cost": face1.get("mana_cost"),
            "cores": ", ".join(face1.get("colors", [])),
            "imagem": face1.get("image_uris", {}).get("normal") or carta.get("image_uris", {}).get("normal"),
            "nome_2": face2.get("name"),
            "imagem_2": face2.get("image_uris", {}).get("normal"),
            "colecao_nome": carta.get("set_name"),
            "icone_colecao": carta.get("set_icon_svg_uri"),
            "raridade": carta.get("rarity"),
            "tipo": carta.get("type_line"),
            "preco_brl": preco_brl,
            "preco_brl_foil": preco_brl_foil
        }

    df_detalhes = df.apply(lambda linha: pd.Series(
        detalhes_dict.get((linha["colecao"], linha["numero"]), {})
    ), axis=1)

    return pd.concat([df, df_detalhes], axis=1)
