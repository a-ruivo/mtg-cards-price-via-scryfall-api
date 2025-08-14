import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import plotly.graph_objects as go
from PIL import Image

from config import CSV_PATH, REPO, GITHUB_TOKEN
from utils.api import buscar_detalhes_com_lotes, get_usd_to_brl
from utils.github import carregar_csv, salvar_csv_em_github, alterar_csv_em_github, carregar_csv_sem_cache
from utils.helpers import gerar_icones, preparar_dataframe, limpar_e_enriquecer_dataframe, autenticar, get_mana_map, extrair_detalhes_cartas

if "aba_atual" not in st.session_state:
    st.session_state["aba_atual"] = "Coleção"

st.set_page_config(page_title="MTG Card Collection", layout="wide")

aba_atual = st.sidebar.radio("Pages", ["Collection", "Dashboard", "Add Card", "Import File", "Card Manager"])
st.session_state["aba_atual"] = aba_atual

# Carrega a imagem da pasta local
image = Image.open("doc/capa.png")

# Exibe a imagem no topo
st.image(image, use_container_width=True)

st.markdown("""
**Made by Allan Ruivo Wildner | https://github.com/a-ruivo**  
""")


reprocessar = st.button("Refresh Data", help="Reprocess the data from the CSV file and update the collection.")

if reprocessar:
    df = carregar_csv_sem_cache()

    # Remove duplicatas antes de qualquer processamento
    df = df.drop_duplicates(subset=["colecao", "numero"], keep="last")

    # Mantém apenas as colunas relevantes
    df = df.loc[:, ["colecao", "numero", "padrao", "foil", "obs"]]

    # Prepara o DataFrame (se necessário)
    df = preparar_dataframe(df)

    # Atualiza cotação e busca detalhes
    cotacao = get_usd_to_brl()
    identificadores = [{"set": row["colecao"], "collector_number": row["numero"]} for _, row in df.iterrows()]
    todos_detalhes = buscar_detalhes_com_lotes(identificadores)

    # Extrai os detalhes sem duplicar colunas
    df_detalhes = extrair_detalhes_cartas(df, todos_detalhes, cotacao)

    # Salva no GitHub e atualiza o estado
    alterar_csv_em_github(df_detalhes, REPO, CSV_PATH, GITHUB_TOKEN)
    st.session_state["df"] = df_detalhes
    st.success("Data updated!")

else:
    if "df" not in st.session_state:
        st.session_state["df"] = carregar_csv()

# Executa autenticação uma vez
if "autenticado" not in st.session_state:
    autenticar()

acesso_restrito = not st.session_state.get("autenticado", False)

if st.session_state["aba_atual"] == "Collection":
    df = st.session_state["df"]
    df, colecao_map = limpar_e_enriquecer_dataframe(df)
    mana_map = get_mana_map()

    # Ordenação
    ordenar_por = st.sidebar.selectbox("Order by", ["Name", "Color", "Value", "Mana Cost","Collection", "Type", "Rarity", "Card Number", "Quantity Regular", "Quantity Foil"])
    ordem = st.sidebar.radio("Order", ["Ascending", "Decreasing"])

    coluna_ordem = {
        "Name": "nome",
        "Color": "cores",
        "Value": "valor_total_brl",
        "Mana Cost": "mana_cost",
        "Collection": "colecao",
        "Type": "tipo",
        "Rarity": "raridade",
        "Card Number": "numero",
        "Quantity Regular": "padrao",
        "Quantity Foil": "foil"
    }[ordenar_por]

    df = df.sort_values(by=coluna_ordem, ascending=(ordem == "Ascending"))

    colecao_opcoes = sorted(df["colecao"].unique())
    colecao_labels = ["All"] + [colecao_map[c]["nome"] for c in colecao_opcoes]
    colecao_escolhida_label = st.sidebar.multiselect("Collection", colecao_labels, default=["All"])

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

    # Filtro por nome da carta
    nome_busca = st.sidebar.text_input("Search by card name")
    if nome_busca:
        df = df[df["nome"].str.contains(nome_busca, case=False, na=False)]

    # Filtro por tipo
    tipos_disponiveis = sorted(df["tipo"].dropna().unique())
    tipo_escolhido = st.sidebar.multiselect("Card Type", ["All"] + tipos_disponiveis, default=["All"])
    if "All" not in tipo_escolhido:
        df = df[df["tipo"].isin(tipo_escolhido)]

    # Filtro por valor
    valor_maximo = float(df["valor_total_brl"].dropna().max())
    if pd.isna(valor_maximo) or valor_maximo == 0.0:
        valor_maximo = 1.0  # fallback seguro
    valor_min, valor_max = st.sidebar.slider(
        "Card Value (BRL)",
        0.0,
        valor_maximo,
        (0.0, valor_maximo)
    )

    # Corrige caso os valores sejam iguais
    if valor_min == valor_max:
        valor_max += 1.0

    df = df[(df["valor_total_brl"] >= valor_min) & (df["valor_total_brl"] <= valor_max)]


    # Filtro por tipo de posse
    opcoes_posse = ["All", "Only Regular", "Only Foil", "Both"]
    posse_escolhida = st.sidebar.selectbox("Face Type", opcoes_posse)
    if posse_escolhida == "Only Regular":
        df = df[df["padrao"].astype(int) > 0]
    elif posse_escolhida == "Only Foil":
        df = df[df["foil"].astype(int) > 0]
    elif posse_escolhida == "Both":
        df = df[(df["padrao"].astype(int) > 0) & (df["foil"].astype(int) > 0)]

    col1, col2, col3, col4 = st.columns(4)

    total_cartas = df["padrao"].sum() + df["foil"].sum()
    total_padroes = df["padrao"].sum()
    total_foils = df["foil"].sum()
    valor_total = df["valor_total_brl"].sum()

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
                    st.markdown(f"**Collection Code:** {carta.colecao}")
                    st.markdown(f"**Card Number:** {carta.numero}")
                    st.markdown(f"**Rarity:** {carta.raridade.capitalize()}")
                    st.markdown(f"**Price (BRL):** R${carta.preco_brl}")
                    st.markdown(f"**Quantity (Regular):** {carta.padrao}")
                    st.markdown(f"**Quantity (Foil):** {carta.foil}")
                    tem_segunda_face = "No" if pd.notna(getattr(carta, "nome_2", None)) else "Yes"
                    st.markdown(f"**Secondary effect or face:** {tem_segunda_face}")

elif st.session_state["aba_atual"] == "Dashboard":
    st.header("Dashboard")
    
    df = st.session_state["df"]

    df, colecao_map = limpar_e_enriquecer_dataframe(df)
    mana_map = get_mana_map()

    colecao_opcoes = sorted(df["colecao"].unique())
    colecao_labels = ["All"] + [colecao_map[c]["nome"] for c in colecao_opcoes]
    colecao_escolhida_label = st.sidebar.multiselect("Collection", colecao_labels, default=["All"])

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

    # Filtro por nome da carta
    nome_busca = st.sidebar.text_input("Search by card name")
    if nome_busca:
        df = df[df["nome"].str.contains(nome_busca, case=False, na=False)]

    # Filtro por tipo
    tipos_disponiveis = sorted(df["tipo"].dropna().unique())
    tipo_escolhido = st.sidebar.multiselect("Card Type", ["All"] + tipos_disponiveis, default=["All"])
    if "All" not in tipo_escolhido:
        df = df[df["tipo"].isin(tipo_escolhido)]

    # Filtro por valor
    valor_maximo = float(df["valor_total_brl"].dropna().max())
    if pd.isna(valor_maximo) or valor_maximo == 0.0:
        valor_maximo = 1.0  # fallback seguro
    valor_min, valor_max = st.sidebar.slider(
        "Card Value (BRL)",
        0.0,
        valor_maximo,
        (0.0, valor_maximo)
    )

    # Corrige caso os valores sejam iguais
    if valor_min == valor_max:
        valor_max += 1.0

    df = df[(df["valor_total_brl"] >= valor_min) & (df["valor_total_brl"] <= valor_max)]


    # Filtro por tipo de posse
    opcoes_posse = ["All", "Only Regular", "Only Foil", "Both"]
    posse_escolhida = st.sidebar.selectbox("Face Type", opcoes_posse)
    if posse_escolhida == "Only Regular":
        df = df[df["padrao"].astype(int) > 0]
    elif posse_escolhida == "Only Foil":
        df = df[df["foil"].astype(int) > 0]
    elif posse_escolhida == "Both":
        df = df[(df["padrao"].astype(int) > 0) & (df["foil"].astype(int) > 0)]

    col1, col2, col3, col4 = st.columns(4)

    total_cartas = df["padrao"].sum() + df["foil"].sum()
    total_padroes = df["padrao"].sum()
    total_foils = df["foil"].sum()
    valor_total = df["valor_total_brl"].sum()

    col1.metric("Total Cards:", f"{total_cartas:,}")
    col2.metric("Regular Cards:", f"{total_padroes:,}")
    col3.metric("Foil Cards:", f"{total_foils:,}")
    col4.metric("Total Value (BRL)", f"R$ {valor_total:,.2f}")
    st.markdown("---")

    # Paleta de cores das manas
    mana_colors = {
        "W": "#ffffe0",
        "U": "#87cefa",
        "B": "#696969",
        "R": "#ff7f50",
        "G": "#7cfc00",
        "C": "#d3d3d3",
        "L": "#e6e6fa"
    }

    # Cartas por cor
    df["quantidade_total"] = df["padrao"] + df["foil"]
    df_cores = df.copy()
    df_cores["cores"] = df_cores["cores"].fillna("").str.split(", ")
    df_cores = df_cores.explode("cores")
    cores_contagem = df_cores.groupby("cores")["quantidade_total"].sum().sort_values(ascending=True)


    

    # Cores suaves
    mana_colors_soft = {
        "W": "#fdfd96",   # amarelo claro
        "U": "#add8e6",   # azul claro
        "B": "#a9a9a9",   # cinza médio
        "R": "#ffb6b6",   # vermelho claro
        "G": "#90ee90",   # verde claro
        "C": "#d3d3d3",   # cinza claro
        "L": "#e6e6fa"    # lavanda
    }

    # Ícones de mana (SVGs hospedados)
    mana_icons = {
        "W": "https://svgs.scryfall.io/card-symbols/W.svg",
        "U": "https://svgs.scryfall.io/card-symbols/U.svg",
        "B": "https://svgs.scryfall.io/card-symbols/B.svg",
        "R": "https://svgs.scryfall.io/card-symbols/R.svg",
        "G": "https://svgs.scryfall.io/card-symbols/G.svg",
        "C": "https://svgs.scryfall.io/card-symbols/C.svg",
        "L": "https://svgs.scryfall.io/card-symbols/L.svg"
    }


    fig1 = go.Figure()

    # Adiciona barras e ícones
    for cor, valor in cores_contagem.items():
        fig1.add_trace(go.Bar(
            x=[valor],
            y=[cor],
            orientation='h',
            marker=dict(
                color=mana_colors_soft.get(cor, "#999999"),
                line=dict(width=0)
            ),
            text=str(valor),
            textposition='outside', 
            cliponaxis=False,
            insidetextanchor='end',
            hoverinfo='none',
            textfont=dict(size=16,color="white")
        ))

        # Adiciona ícone com altura proporcional à barra
        fig1.add_layout_image(
            dict(
                source=mana_icons.get(cor),
                xref="paper",
                yref="y",
                x=-0.08,  # ⬅ mais à esquerda
                y=cor,
                sizex=0.06,
                sizey=1.0,  # ⬅ altura igual à faixa da barra
                xanchor="left",
                yanchor="middle",
                layer="above"
            )
        )

    # Layout do gráfico
    fig1.update_layout(
        title_text='Card quantity by mana color',
        title_x=0.0,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white'),
        xaxis=dict(
            visible=False,
            showticklabels=False,
            showgrid=False,
            ticks=""
        ),
        yaxis=dict(
            showticklabels=False,  # ⬅ remove os rótulos de texto
            title=None             # ⬅ remove o nome do eixo
        ),
        margin=dict(l=100, r=80, t=40, b=30)  # ⬅ mais espaço à esquerda
    )

    fig1.update_layout(showlegend=False)



    # Cartas por coleção
    colecao_contagem = df.groupby("colecao_nome")["quantidade_total"].sum().sort_values(ascending=True)

    # Criação do gráfico
    fig2 = go.Figure()

    for colecao_nome, quantidade_total in colecao_contagem.items():
        fig2.add_trace(go.Bar(
            x=[quantidade_total],
            y=[str(colecao_nome)],
            orientation='h',
            marker=dict(color="#D3D3D3", line=dict(width=0)),
            text=str(quantidade_total),
            textposition='outside',
            cliponaxis=False,
            insidetextanchor='end',
            hoverinfo='none',
            textfont=dict(size=16,color="white")
        ))

    # Estilo do gráfico
    fig2.update_layout(
        title_text='Collection distribution',
        height=3000,
        title_x=0.0,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white'),
        xaxis=dict(
            visible=False,
            showticklabels=False,
            showgrid=False,
            ticks=""
        ),
        yaxis=dict(showticklabels=True, title=None),
        margin=dict(l=100, r=80, t=40, b=30),
        showlegend=False
    )

    import re

    # Função para calcular o custo total de mana
    def calcular_mana_total(mana_cost):
        if pd.isna(mana_cost):
            return 0
        partes = re.findall(r'\d+|[WUBRGCL]', mana_cost)
        total = 0
        for p in partes:
            if p.isdigit():
                total += int(p)
            else:
                total += 1
        return total

    # Aplica a função e agrupa
    df["mana_total"] = df["mana_cost"].apply(calcular_mana_total)
    mana_total_contagem = df.groupby("mana_total")["quantidade_total"].sum().sort_index()

    # Dicionário de ícones de custo de mana da Scryfall
    mana_cost_icons = {
        i: f"https://svgs.scryfall.io/card-symbols/{i}.svg" for i in mana_total_contagem.index
    }

    # Criação do gráfico
    fig3 = go.Figure()

    for custo, quantidade in mana_total_contagem.items():
        fig3.add_trace(go.Bar(
            x=[quantidade],
            y=[str(custo)],
            orientation='h',
            marker=dict(color="#D3D3D3", line=dict(width=0)),
            text=str(quantidade),
            textposition='outside',
            cliponaxis=False,
            insidetextanchor='end',
            hoverinfo='none',
            textfont=dict(size=16,color="white")
        ))

        # Ícone no lugar do rótulo
        fig3.add_layout_image(
            dict(
                source=mana_cost_icons.get(custo),
                xref="paper",
                yref="y",
                x=-0.08,
                y=str(custo),
                sizex=0.06,
                sizey=1.0,
                xanchor="left",
                yanchor="middle",
                layer="above"
            )
        )

    # Estilo do gráfico
    fig3.update_layout(
        title_text='Mana cost distribution',
        title_x=0.0,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white'),
        xaxis=dict(
            visible=False,
            showticklabels=False,
            showgrid=False,
            ticks=""
        ),
        yaxis=dict(showticklabels=False, title=None),
        margin=dict(l=100, r=80, t=40, b=30),
        showlegend=False
    )

    # Cartas por tipo
    def extrair_antes_do_traco(texto):
        if pd.isna(texto):
            return ""
        # Tenta dividir por em dash (—) ou en dash (–)
        partes = re.split(r"—|–", texto)
        return partes[0].strip() if partes else texto.strip()

    df["tipo_sem_traco"] = df["tipo"].apply(extrair_antes_do_traco)
    tipo_contagem = df.groupby("tipo_sem_traco")["quantidade_total"].sum().sort_values(ascending=True)



    # Criação do gráfico
    fig4 = go.Figure()

    for tipo_sem_traco, quantidade_total in tipo_contagem.items():
        fig4.add_trace(go.Bar(
            x=[quantidade_total],
            y=[str(tipo_sem_traco)],
            orientation='h',
            marker=dict(color="#D3D3D3", line=dict(width=0)),
            text=str(quantidade_total),
            textposition='outside',
            cliponaxis=False,
            insidetextanchor='end',
            hoverinfo='none',
            textfont=dict(size=16,color="white")
        ))

    # Estilo do gráfico
    fig4.update_layout(
        title_text='Card type distribution',
        title_x=0.0,
        height=1000,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white'),
        xaxis=dict(
            visible=False,
            showticklabels=False,
            showgrid=False,
            ticks="",
        ),
        yaxis=dict(showticklabels=True, title=None),
        margin=dict(l=100, r=80, t=40, b=30),
        showlegend=False
    )

    col1, col2 = st.columns([1, 1])  # proporções iguais

    with col1:
        st.plotly_chart(fig1, use_container_width=True)
        st.plotly_chart(fig2, use_container_width=True)

    with col2:
        st.plotly_chart(fig3, use_container_width=True)
        st.plotly_chart(fig4, use_container_width=True)

elif st.session_state["aba_atual"] == "Add Card":
    st.header("Add card manually or by code")
    df_existente = st.session_state["df"]

    if acesso_restrito:
        st.warning("Enter the password to access this page.")
        st.stop()

    modo = st.radio("Mode", ["Manual", "Search by code"])

    if modo == "Search by code":
        codigo_colecao_add = st.text_input("Collection code")
        numero_carta_add = st.text_input("Card number")
        padrao_add = st.number_input("Regular quantity", min_value=0)
        foil_add = st.number_input("Foil quantity", min_value=0)
        buscar = st.button("Search and save")

        if buscar and codigo_colecao_add and numero_carta_add:
            if padrao_add == 0 and foil_add == 0:
                st.warning("At least one of the quantitys must be different then 0.")
            else:
                identificador = [{"set": codigo_colecao_add.lower(), "collector_number": numero_carta_add}]
                dados = buscar_detalhes_com_lotes(identificador)
                if dados:
                    carta_add = dados[0]
                    cotacao_add = get_usd_to_brl()
                    preco_usd_add = float(carta_add.get("prices", {}).get("usd") or 0)
                    preco_foil_add = float(carta_add.get("prices", {}).get("usd_foil") or 0)
                    preco_brl_add = round(preco_usd_add * cotacao_add, 2)
                    preco_brl_foil_add = round(preco_foil_add * cotacao_add, 2)
                    imagem_add = carta_add.get("image_uris", {}).get("normal")

                    nova = pd.DataFrame([{
                        "nome": carta_add.get("name"),
                        "tipo": carta_add.get("type_line"),
                        "preco_brl": preco_brl_add,
                        "preco_brl_foil": preco_brl_foil_add,
                        "padrao": padrao_add,
                        "foil": foil_add,
                        "imagem": imagem_add,
                        "colecao": codigo_colecao_add.lower(),
                        "numero": numero_carta_add,
                        "colecao_nome": carta_add.get("set_name"),
                        "icone_colecao": carta_add.get("set_icon_svg_uri"),
                        "raridade": carta_add.get("rarity"),
                        "cores": ", ".join(carta_add.get("colors", [])),
                        "mana_cost": carta_add.get("mana_cost"),
                        "nome_2": None
                    }])

                    ja_existe = (
                        (df_existente["colecao"] == nova["colecao"].iloc[0]) &
                        (df_existente["numero"] == nova["numero"].iloc[0])
                    ).any()

                    if ja_existe:
                        st.warning("This card already is in the collection.")
                    else:
                        df_add = pd.concat([df_existente, nova], ignore_index=True)
                        sucesso = salvar_csv_em_github(df_add, REPO, CSV_PATH, GITHUB_TOKEN)
                        if sucesso:
                            st.session_state["df"] = df_add
                            st.success("Card added!")
                        else:
                            st.error("Error saving in GitHub.")
                else:
                    st.error("Card not found in API.")
    else:
        with st.form("form_carta"):
            nome_form = st.text_input("Card name")
            tipo_form = st.text_input("Type")
            preco_brl_form = st.number_input("Price (BRL)", min_value=0.0)
            preco_brl_foil_form = st.number_input("Price Foil (BRL)", min_value=0.0)
            padrao_form = st.number_input("Regular quantity", min_value=0)
            foil_form = st.number_input("Foil quantity", min_value=0)
            imagem_form = st.text_input("Image URL")
            colecao_form = st.text_input("Collection code")
            numero_form = st.text_input("Card number")
            colecao_nome_form = st.text_input("Collection name")
            icone_colecao_form = st.text_input("Collection icon URL")
            raridade_form = st.selectbox("Rarity", ["common", "uncommon", "rare", "mythic"])
            cores_form = st.text_input("Colors (ex: W, U, B, R, G, C, L)")
            mana_cost_form = st.text_input("Mana cost (ex: {1}{G}{G})")
            nome_2_form = st.text_input("Alternative name or secondary face (optional)")
            enviado = st.form_submit_button("Add card")

        if enviado:
            if padrao_form == 0 and foil_form == 0:
                st.warning("At least one of the quantitys must be different then 0.")
            else:
                nova_carta = pd.DataFrame([{
                    "nome": nome_form, "tipo": tipo_form, "preco_brl": preco_brl_form, "preco_brl_foil": preco_brl_foil_form,
                    "padrao": padrao_form, "foil": foil_form, "imagem": imagem_form, "colecao": colecao_form,
                    "numero": numero_form, "colecao_nome": colecao_nome_form, "icone_colecao": icone_colecao_form,
                    "raridade": raridade_form, "cores": cores_form, "mana_cost": mana_cost_form, "nome_2": nome_2_form
                }])

                ja_existe = (
                    (df_existente["colecao"] == nova_carta["colecao"].iloc[0]) &
                    (df_existente["numero"] == nova_carta["numero"].iloc[0])
                ).any()

                if ja_existe:
                    st.warning("This card already is in the collection.")
                else:
                    df_form = pd.concat([df_existente, nova_carta], ignore_index=True)
                    sucesso, mensagem = salvar_csv_em_github(df_form, REPO, CSV_PATH, GITHUB_TOKEN)
                    if sucesso:
                        st.session_state["df"] = df_form
                        st.success("Card added!")
                    else:
                        st.error(f"Error saving in GitHub: {mensagem}")

elif st.session_state["aba_atual"] == "Import File":
    st.header("Import cards from Excel file")

    if acesso_restrito:
        st.warning("Enter the password to access this page.")
        st.stop()

    arquivo = st.file_uploader("Select the Excel file", type=["xlsx"])
    executar_importacao = st.button("Import")

    if executar_importacao and arquivo:
        df_file = pd.read_excel(arquivo)
        df_file = df_file.dropna(subset=["colecao", "numero"])
        df_file["colecao"] = df_file["colecao"].astype(str).str.lower()
        df_file["numero"] = df_file["numero"].astype(str)
        df_file["padrao"] = df_file.get("padrao", 1)
        df_file["foil"] = df_file.get("foil", 0)

        df_file = df_file.groupby(["colecao", "numero"], as_index=False).agg({
            "padrao": "sum",
            "foil": "sum",
            **{col: "first" for col in df_file.columns if col not in ["colecao", "numero", "padrao", "foil"]}
        })

        cotacao_file = get_usd_to_brl()
        identificadore2 = [{"set": row["colecao"], "collector_number": row["numero"]} for _, row in df_file.iterrows()]
        todos_detalhes2 = buscar_detalhes_com_lotes(identificadore2)

        df_manager = extrair_detalhes_cartas(df_file, todos_detalhes2, cotacao_file)

        df_final = pd.concat([df_file, df_manager], axis=1)
        sucesso, mensagem = salvar_csv_em_github(df_final, REPO, CSV_PATH, GITHUB_TOKEN)

        if sucesso:
            st.success("Cards add!")
        else:
            st.error(f"Error saving in GitHub: {mensagem}")

elif st.session_state["aba_atual"] == "Card Manager":
        st.header("Card Manager")
        df_manager = st.session_state["df"]

        if acesso_restrito:
            st.warning("Enter the password to access this page.")
            st.stop()

        try:
            def csv(path):
                return pd.read_csv(path)

            df_manager = csv(CSV_PATH)

            # Converte colunas numéricas com segurança
            df_manager["padrao"] = pd.to_numeric(df_manager["padrao"], errors="coerce").fillna(0).replace([float("inf"), float("-inf")], 0).astype(int) 
            df_manager["foil"] = pd.to_numeric(df_manager["foil"], errors="coerce").fillna(0).replace([float("inf"), float("-inf")], 0).astype(int)


            # Editor completo
            df_editado = st.data_editor(
                df_manager,
                num_rows="dynamic",
                use_container_width=True,
                key="editor"
            )

            # Botão de salvar
            if st.button("Save"):
                sucesso, mensagem = alterar_csv_em_github(df_editado, REPO, CSV_PATH, GITHUB_TOKEN)
                if sucesso:
                    st.success("Changes saved!")
                else:
                    st.error(f"Error saving in GitHub: {mensagem}")

        except:
            st.warning("Data not found.")