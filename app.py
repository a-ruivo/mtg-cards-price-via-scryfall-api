import streamlit as st
import pandas as pd

st.set_page_config(page_title="Cartas Magic", layout="wide")

@st.cache_data
def carregar_dados():
    return pd.read_csv("cartas_magic_detalhadas.csv")

# Carregar dados
df = carregar_dados()
df["cores"] = df.apply(
    lambda row: "L" if "Land" in str(row["tipo"]) else (
        "C" if pd.isna(row["cores"]) or str(row["cores"]).strip() == "" else row["cores"]
    ),
    axis=1
)
df["mana_cost"] = df.apply(
    lambda row: "L" if "Land" in str(row["tipo"]) else (
        "C" if pd.isna(row["mana_cost"]) or str(row["mana_cost"]).strip() == "" else row["mana_cost"]
    ),
    axis=1
)
df = df.astype(str)

# Preparar ícones de coleção
colecao_map = {
    row["colecao"]: {
        "nome": row["colecao_nome"],
        "icone": row["icone_colecao"]
    }
    for _, row in df.drop_duplicates(subset=["colecao"]).iterrows()
}

# Ícones de mana
mana_map = {
    # Cores básicas
    "W": "https://svgs.scryfall.io/card-symbols/W.svg",
    "U": "https://svgs.scryfall.io/card-symbols/U.svg",
    "B": "https://svgs.scryfall.io/card-symbols/B.svg",
    "R": "https://svgs.scryfall.io/card-symbols/R.svg",
    "G": "https://svgs.scryfall.io/card-symbols/G.svg",
    "C": "https://svgs.scryfall.io/card-symbols/C.svg",
    "L": "https://svgs.scryfall.io/card-symbols/L.svg",
    "S": "https://svgs.scryfall.io/card-symbols/S.svg",

    # Combinadas híbridas
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

    # Híbridas com phyrexian
    "W/P": "https://svgs.scryfall.io/card-symbols/WP.svg",
    "U/P": "https://svgs.scryfall.io/card-symbols/UP.svg",
    "B/P": "https://svgs.scryfall.io/card-symbols/BP.svg",
    "R/P": "https://svgs.scryfall.io/card-symbols/RP.svg",
    "G/P": "https://svgs.scryfall.io/card-symbols/GP.svg",
    "C/P": "https://svgs.scryfall.io/card-symbols/CP.svg",

    # Híbridas com genérico
    "2/W": "https://svgs.scryfall.io/card-symbols/2W.svg",
    "2/U": "https://svgs.scryfall.io/card-symbols/2U.svg",
    "2/B": "https://svgs.scryfall.io/card-symbols/2B.svg",
    "2/R": "https://svgs.scryfall.io/card-symbols/2R.svg",
    "2/G": "https://svgs.scryfall.io/card-symbols/2G.svg",

    # Colorless + color
    "C/W": "https://svgs.scryfall.io/card-symbols/CW.svg",
    "C/U": "https://svgs.scryfall.io/card-symbols/CU.svg",
    "C/B": "https://svgs.scryfall.io/card-symbols/CB.svg",
    "C/R": "https://svgs.scryfall.io/card-symbols/CR.svg",
    "C/G": "https://svgs.scryfall.io/card-symbols/CG.svg",

    # Metade de mana
    "HW": "https://svgs.scryfall.io/card-symbols/HW.svg",
    "HR": "https://svgs.scryfall.io/card-symbols/HR.svg",

    # Outros
    "X": "https://svgs.scryfall.io/card-symbols/X.svg",
    "T": "https://svgs.scryfall.io/card-symbols/T.svg",
    "Q": "https://svgs.scryfall.io/card-symbols/Q.svg",
    "E": "https://svgs.scryfall.io/card-symbols/E.svg",
    "A": "https://svgs.scryfall.io/card-symbols/A.svg",
    "CHAOS": "https://svgs.scryfall.io/card-symbols/CHAOS.svg",
    "PW": "https://svgs.scryfall.io/card-symbols/PW.svg",
}


# Sidebar
st.sidebar.title("Filters")

# Filtro de coleção
colecao_opcoes = sorted(df["colecao"].unique())
colecao_labels = ["All"] + [colecao_map[c]["nome"] for c in colecao_opcoes]
colecao_escolhida_label = st.sidebar.multiselect("Coleção", colecao_labels, default=["All"])

if "All" not in colecao_escolhida_label:
    colecao_escolhida = [
        c for c in colecao_opcoes if colecao_map[c]["nome"] in colecao_escolhida_label
    ]
    df = df[df["colecao"].isin(colecao_escolhida)]

# Filtro de cor
cores_disponiveis = sorted(set("".join(df["cores"].dropna().unique()).replace(",", "").replace(" ", "")))
opcoes_cores = ["All"] + cores_disponiveis
cor_escolhida = st.sidebar.multiselect("Cor", opcoes_cores, default=["All"])

if "All" not in cor_escolhida:
    df = df[df["cores"].apply(lambda x: any(c in x for c in cor_escolhida if isinstance(x, str)))]

# Mostrar ícones das cores selecionadas
st.sidebar.markdown("### Colors selected:")
for cor in cor_escolhida:
    if cor in mana_map:
        st.sidebar.image(mana_map[cor], width=40)

# Exibir cartas
st.title("Allan & Ayla MTG Cards Collection")

for _, carta in df.iterrows():
    col1, col2 = st.columns([1, 5])
    with col1:
        st.image(carta["imagem"], width=300, caption=carta["nome"])
    with col2:
        # tipo
        st.markdown(f"**Type:** {carta['tipo']}")
        # custo mana
        cores = carta["mana_cost"].split(",")
        icones = []
        for cor in cores:
            cor = cor.strip()
            if cor in mana_map:
                icones.append(f'<img src="{mana_map[cor]}" width="25">')
            else:
                icones.append(cor)
        st.markdown("**Mana Cost:** " + " ".join(icones), unsafe_allow_html=True)

        # Ícones das cores
        cores = carta["cores"].split(",")
        icones = []
        for cor in cores:
            cor = cor.strip()
            if cor in mana_map:
                icones.append(f'<img src="{mana_map[cor]}" width="25">')
            else:
                icones.append(cor)
        st.markdown("**Colors:** " + " ".join(icones), unsafe_allow_html=True)

        st.markdown(f"**Collection:** {carta['colecao_nome']}")
        st.markdown(f"**Rarity:** {carta['raridade'].capitalize()}")
        st.markdown(f"**Price (BRL):** R${carta['preco_brl']}")
    st.markdown("---")
