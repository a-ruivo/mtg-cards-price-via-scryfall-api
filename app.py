import streamlit as st
import pandas as pd

st.set_page_config(page_title="Cartas Magic", layout="wide")

@st.cache_data
def carregar_dados():
    return pd.read_csv("cartas_magic_detalhadas.csv")

def gerar_icones(valores, mapa):
    icones = []
    for v in str(valores).split(","):
        v = v.strip()
        if v in mapa:
            icones.append(f'<img src="{mapa[v]}" width="25">')
        else:
            icones.append(v)
    return " ".join(icones)

# Carregar dados
df = carregar_dados()
df["cores"] = df.apply(
    lambda row: "L" if "Land" in str(row["tipo"]) else (
        "C" if pd.isna(row["cores"]) or str(row["cores"]).strip() == "" else row["cores"]
    ),
    axis=1
)

df = df.astype(str)
df["mana_cost"] = df["mana_cost"].astype(str)
df["mana_cost"] = df["mana_cost"].str.replace("nan", "", regex=False)
df["mana_cost"] = df["mana_cost"].str.replace("//", "/", regex=False)
df["mana_cost"] = df["mana_cost"].str.replace("{", "", regex=False)
df["mana_cost"] = df["mana_cost"].str.replace("}", "", regex=False)
df["padrao"] = df["padrao"].astype(int)
df["foil"] = df["foil"].astype(int)

df["valor_total_brl"] = (
    df["padrao"] * df["preco_brl"].astype(float) +
    df["foil"] * df["preco_brl_foil"].astype(float)
)

total_cartas = df["padrao"].sum() + df["foil"].sum()
total_padroes = df["padrao"].sum()
total_foils = df["foil"].sum()
valor_total = df["valor_total_brl"].sum()

colecao_map = {
    row["colecao"]: {
        "nome": row["colecao_nome"],
        "icone": row["icone_colecao"]
    }
    for _, row in df.drop_duplicates(subset=["colecao"]).iterrows()
}

mana_map = {
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

st.sidebar.title("Filters")

# Ordenação
ordenar_por = st.sidebar.selectbox("Ordenar por", ["Nome", "Cor", "Valor"])
ordem = st.sidebar.radio("Ordem", ["Ascendente", "Descendente"])

coluna_ordem = {
    "Nome": "nome",
    "Cor": "cores",
    "Valor": "valor_total_brl"
}[ordenar_por]

df = df.sort_values(by=coluna_ordem, ascending=(ordem == "Ascendente"))

colecao_opcoes = sorted(df["colecao"].unique())
colecao_labels = ["All"] + [colecao_map[c]["nome"] for c in colecao_opcoes]
colecao_escolhida_label = st.sidebar.multiselect("Coleção", colecao_labels, default=["All"])

if "All" not in colecao_escolhida_label:
    colecao_escolhida = [
        c for c in colecao_opcoes if colecao_map[c]["nome"] in colecao_escolhida_label
    ]
    df = df[df["colecao"].isin(colecao_escolhida)]

cores_disponiveis = sorted(set(
    cor.strip() for lista in df["cores"].dropna().str.split(",") for cor in lista
))
opcoes_cores = ["All"] + cores_disponiveis
cor_escolhida = st.sidebar.multiselect("Cor", opcoes_cores, default=["All"])

if "All" not in cor_escolhida:
    df = df[df["cores"].apply(lambda x: any(c in x for c in cor_escolhida if isinstance(x, str)))]

st.sidebar.markdown("### Colors selected:")
for cor in cor_escolhida:
    if cor in mana_map:
        st.sidebar.image(mana_map[cor], width=40)

# Filtro por nome da carta
nome_busca = st.sidebar.text_input("Buscar por nome da carta")
if nome_busca:
    df = df[df["nome"].str.contains(nome_busca, case=False, na=False)]

# Filtro por tipo
tipos_disponiveis = sorted(df["tipo"].dropna().unique())
tipo_escolhido = st.sidebar.multiselect("Tipo", ["All"] + tipos_disponiveis, default=["All"])
if "All" not in tipo_escolhido:
    df = df[df["tipo"].isin(tipo_escolhido)]

# Filtro por valor
valor_min, valor_max = st.sidebar.slider("Filtrar por valor total (BRL)", 0.0, float(df["valor_total_brl"].max()), (0.0, float(df["valor_total_brl"].max())))
df = df[(df["valor_total_brl"] >= valor_min) & (df["valor_total_brl"] <= valor_max)]

# Filtro por tipo de posse
opcoes_posse = ["Todos", "Apenas Regular", "Apenas Foil", "Ambos"]
posse_escolhida = st.sidebar.selectbox("Tipo de posse", opcoes_posse)
if posse_escolhida == "Apenas Regular":
    df = df[df["padrao"].astype(int) > 0]
elif posse_escolhida == "Apenas Foil":
    df = df[df["foil"].astype(int) > 0]
elif posse_escolhida == "Ambos":
    df = df[(df["padrao"].astype(int) > 0) & (df["foil"].astype(int) > 0)]


st.title("Allan & Ayla MTG Cards Collection")

col1, col2, col3, col4 = st.columns(4)

col1.metric("Total Cards:", f"{total_cartas:,}")
col2.metric("Regular Cards:", f"{total_padroes:,}")
col3.metric("Foil Cards:", f"{total_foils:,}")
col4.metric("Total Value (BRL)", f"R$ {valor_total:,.2f}")
st.markdown("---")

num_colunas = 4
for i in range(0, len(df), num_colunas):
    linha = df.iloc[i:i+num_colunas]
    cols = st.columns(len(linha))  # só cria o número necessário de colunas
    for idx, carta in enumerate(linha.itertuples()):
        with cols[idx]:
            if pd.notna(carta.imagem):
                st.image(carta.imagem, use_container_width=True, caption=carta.nome)
            with st.expander("Details", expanded=False):
                st.markdown(f"**Type:** {carta.tipo}")
                st.markdown("**Mana Cost:** " + gerar_icones(carta.mana_cost, mana_map), unsafe_allow_html=True)
                st.markdown("**Colors:** " + gerar_icones(carta.cores, mana_map), unsafe_allow_html=True)
                st.markdown(f"**Collection:** {carta.colecao_nome}")
                st.markdown(f"**Rarity:** {carta.raridade.capitalize()}")
                st.markdown(f"**Price (BRL):** R${carta.preco_brl}")
                st.markdown(f"**Quantity (Regular):** {carta.padrao}")
                st.markdown(f"**Quantity (Foil):** {carta.foil}")
                tem_segunda_face = "No" if pd.notna(getattr(carta, "nome_2", None)) else "Yes"
                st.markdown(f"**Secondary effect or face:** {tem_segunda_face}")
