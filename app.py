import streamlit as st
import pandas as pd
import time

from config import CSV_PATH, REPO, GITHUB_TOKEN
from utils.api import buscar_detalhes_com_lotes, get_usd_to_brl
from utils.github import carregar_csv, salvar_csv_em_github, alterar_csv_em_github, carregar_csv_sem_cache
from utils.helpers import gerar_icones, preparar_dataframe, limpar_e_enriquecer_dataframe, autenticar, get_mana_map, extrair_detalhes_cartas

if "aba_atual" not in st.session_state:
    st.session_state["aba_atual"] = "Coleção"

st.set_page_config(page_title="MTG Card Collection", layout="wide")

aba_atual = st.sidebar.radio("Pages", ["Collection", "Dashboard", "Add Card", "Import File", "Card Manager"])
st.session_state["aba_atual"] = aba_atual

st.title("Allan & Ayla MTG Cards Collection")

reprocessar = st.button("Reprocessar dados da coleção")

if reprocessar:
    df = carregar_csv_sem_cache()
    df = df.loc[:, ["colecao", "numero", "padrao", "foil", "obs"]]
    df = preparar_dataframe(df)
    cotacao = get_usd_to_brl()
    identificadores = [{"set": row["colecao"], "collector_number": row["numero"]} for _, row in df.iterrows()]
    todos_detalhes = buscar_detalhes_com_lotes(identificadores)

    df_detalhes = extrair_detalhes_cartas(df, todos_detalhes, cotacao)

    alterar_csv_em_github(df_detalhes, REPO, CSV_PATH, GITHUB_TOKEN)
    st.session_state["df"] = df_detalhes
    st.success("Dados reprocessados com sucesso!")
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
    valor_maximo = float(df["valor_total_brl"].dropna().max())
    if pd.isna(valor_maximo) or valor_maximo == 0.0:
        valor_maximo = 1.0  # fallback seguro
    valor_min, valor_max = st.sidebar.slider(
        "Filtrar por valor total (BRL)",
        0.0,
        valor_maximo,
        (0.0, valor_maximo)
    )

    # Corrige caso os valores sejam iguais
    if valor_min == valor_max:
        valor_max += 1.0

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

elif st.session_state["aba_atual"] == "Add Card":
    st.header("Add card manually or by code")
    df_existente = st.session_state["df"]

    if acesso_restrito:
        st.warning("Você precisa estar autenticado para acessar esta aba.")
        st.stop()

    modo = st.radio("Mode", ["Manual", "Search by code"])

    if modo == "Search by code":
        codigo_colecao_add = st.text_input("Collection code")
        numero_carta_add = st.text_input("Card number")
        padrao_add = st.number_input("Regular quantity", min_value=0)
        foil_add = st.number_input("Foil quantity", min_value=0)
        buscar = st.button("Search and save")

        if buscar and codigo_colecao_add and numero_carta_add:
            identificador = [{"set": codigo_colecao_add.lower(), "collector_number": numero_carta_add}]
            dados = buscar_detalhes_com_lotes(identificador)
            if dados:
                carta = dados[0]
                cotacao_add = get_usd_to_brl()
                preco_usd_add = float(carta.get("prices", {}).get("usd") or 0)
                preco_foil_add = float(carta.get("prices", {}).get("usd_foil") or 0)
                preco_brl_add = round(preco_usd_add * cotacao_add, 2)
                preco_brl_foil_add = round(preco_foil_add * cotacao_add, 2)
                imagem_add = carta.get("image_uris", {}).get("normal")

                nova = pd.DataFrame([{
                    "nome": carta.get("name"),
                    "tipo": carta.get("type_line"),
                    "preco_brl": preco_brl_add,
                    "preco_brl_foil": preco_brl_foil_add,
                    "padrao": padrao_add,
                    "foil": foil_add,
                    "imagem": imagem_add,
                    "colecao": codigo_colecao_add.lower(),
                    "numero": numero_carta_add,
                    "colecao_nome": carta.get("set_name"),
                    "icone_colecao": carta.get("set_icon_svg_uri"),
                    "raridade": carta.get("rarity"),
                    "cores": ", ".join(carta.get("colors", [])),
                    "mana_cost": carta.get("mana_cost"),
                    "nome_2": None
                }])

                ja_existe = (
                    (df_existente["colecao"] == nova["colecao"].iloc[0]) &
                    (df_existente["numero"] == nova["numero"].iloc[0])
                ).any()

                if ja_existe:
                    st.warning("Essa carta já existe na coleção.")
                else:
                    df_add = pd.concat([df_existente, nova], ignore_index=True)
                    sucesso = salvar_csv_em_github(df_add, REPO, CSV_PATH, GITHUB_TOKEN)
                    if sucesso:
                        st.success("Card added!")
                    else:
                        st.error("Error saving to GitHub.")
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
                st.warning("Essa carta já existe na coleção.")
            else:
                df_form = pd.concat([df_existente, nova_carta], ignore_index=True)
                sucesso, mensagem = salvar_csv_em_github(df_form, REPO, CSV_PATH, GITHUB_TOKEN)
                if sucesso:
                    st.success("Card added!")
                else:
                    st.error(f"Erro ao salvar no GitHub: {mensagem}")

elif st.session_state["aba_atual"] == "Import File":
    st.header("Importar cartas via Excel")

    if acesso_restrito:
        st.warning("Você precisa estar autenticado para acessar esta aba.")
        st.stop()

    arquivo = st.file_uploader("Selecione o arquivo Excel", type=["xlsx"])
    executar_importacao = st.button("Executar importação")

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
            st.error(f"Erro ao salvar no GitHub: {mensagem}")

elif st.session_state["aba_atual"] == "Card Manager":
        st.header("Card Manager")
        df_manager = st.session_state["df"]

        if acesso_restrito:
            st.warning("Você precisa estar autenticado para acessar esta aba.")
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
                    st.error(f"Erro ao salvar no GitHub: {mensagem}")

        except:
            st.warning("Data not found.")