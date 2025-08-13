import streamlit as st
import pandas as pd
import requests
import time
import base64
import os

st.set_page_config(page_title="Cartas Magic", layout="wide")

# Verificação de senha
def autenticar():
    senha_correta = st.secrets["senha_app"]
    senha_digitada = st.text_input("Enter the password to edit the collection", type="password")
    if senha_digitada == senha_correta:
        st.session_state["autenticado"] = True
    elif senha_digitada:
        st.error("Wrong password.")

# Configurações do GitHub
GITHUB_TOKEN = st.secrets["github_token"]
REPO = "a-ruivo/mtg-cards-price-via-scryfall-api"
CSV_PATH = "cartas_magic_detalhadas.csv"

# Cotação do dólar
def get_usd_to_brl():
    try:
        r = requests.get("https://economia.awesomeapi.com.br/json/last/USD-BRL")
        return float(r.json()["USDBRL"]["bid"])
    except:
        return 5.0

# Funções auxiliares
def dividir_em_lotes(lista, tamanho):
    for i in range(0, len(lista), tamanho):
        yield lista[i:i + tamanho]

def buscar_detalhes_em_lote(identificadores):
    url = "https://api.scryfall.com/cards/collection"
    r = requests.post(url, json={"identifiers": identificadores})
    return r.json()["data"] if r.status_code == 200 else []


def salvar_csv_em_github(df_novo, repo, path, token):
    import base64, requests, pandas as pd
    from io import StringIO

    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    headers = {"Authorization": f"token {token}"}

    # Verifica se o arquivo já existe
    r_get = requests.get(url, headers=headers)
    if r_get.status_code == 200:
        conteudo_atual = base64.b64decode(r_get.json()["content"]).decode()
        sha = r_get.json()["sha"]
        df_atual = pd.read_csv(StringIO(conteudo_atual))

        # Junta os dados novos com os existentes
        df_final = pd.concat([df_atual, df_novo], ignore_index=True)
    else:
        sha = None
        df_final = df_novo

    # Prepara conteúdo para upload
    conteudo_csv = df_final.to_csv(index=False)
    conteudo_base64 = base64.b64encode(conteudo_csv.encode()).decode()

    data = {
        "message": "Atualização incremental via Streamlit",
        "content": conteudo_base64,
        "branch": "main"
    }
    if sha:
        data["sha"] = sha

    r_put = requests.put(url, headers=headers, json=data)

    if r_put.status_code in [200, 201]:
        return True, "Arquivo salvo com sucesso!"
    else:
        try:
            erro = r_put.json().get("message", "Erro desconhecido")
        except Exception:
            erro = "Erro ao decodificar resposta da API"
        return False, erro

def alterar_csv_em_github(df_novo, repo, path, token):
    import base64, requests

    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    headers = {"Authorization": f"token {token}"}

    # Verifica se o arquivo já existe para obter o SHA
    r_get = requests.get(url, headers=headers)
    sha = r_get.json()["sha"] if r_get.status_code == 200 else None

    # Prepara conteúdo para upload
    conteudo_csv = df_novo.to_csv(index=False)
    conteudo_base64 = base64.b64encode(conteudo_csv.encode()).decode()

    data = {
        "message": "Substituição completa via Streamlit",
        "content": conteudo_base64,
        "branch": "main"
    }
    if sha:
        data["sha"] = sha

    r_put = requests.put(url, headers=headers, json=data)

    if r_put.status_code in [200, 201]:
        return True, "Arquivo salvo com sucesso!"
    else:
        try:
            erro = r_put.json().get("message", "Erro desconhecido")
        except Exception:
            erro = "Erro ao decodificar resposta da API"
        return False, erro


# Abas principais
aba1, aba2, aba3, aba4, aba5 = st.tabs(["Collection", "Login", "Add Card", "Import File", "Card Manager"])

with aba1:
    try:
        @st.cache_data
        def carregar_dados():
            return pd.read_csv(CSV_PATH)

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
        df["padrao"] = df["padrao"].astype(float).astype(int)
        df["foil"] = df["foil"].astype(float).astype(int)

        df["preco_brl"] = df["preco_brl"].replace("nan", "0").astype(float)
        df["preco_brl_foil"] = df["preco_brl_foil"].replace("nan", "0").astype(float)

        df["valor_total_brl"] = (
            df["padrao"] * df["preco_brl"].astype(float) +
            df["foil"] * df["preco_brl_foil"].astype(float)
        )

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


        st.title("Allan & Ayla MTG Cards Collection")

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
                        st.markdown(f"**Rarity:** {carta.raridade.capitalize()}")
                        st.markdown(f"**Price (BRL):** R${carta.preco_brl}")
                        st.markdown(f"**Quantity (Regular):** {carta.padrao}")
                        st.markdown(f"**Quantity (Foil):** {carta.foil}")
                        tem_segunda_face = "No" if pd.notna(getattr(carta, "nome_2", None)) else "Yes"
                        st.markdown(f"**Secondary effect or face:** {tem_segunda_face}")

    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")

with aba2:
    st.header("Login to add cards")
    if "autenticado" not in st.session_state or not st.session_state["autenticado"]:
        autenticar()
        st.stop()

with aba3:
    st.header("Add card mannualy or by code")

    modo = st.radio("Mode", ["Manual", "Search by code"])

    if modo == "Buscar por código":
        codigo_colecao = st.text_input("Collection code")
        numero_carta = st.text_input("Card number")
        padrao = st.number_input("Regular quantity", min_value=0)
        foil = st.number_input("Foil quantity", min_value=0)
        buscar = st.button("Search and save")

        if buscar and codigo_colecao and numero_carta:
            identificador = [{"set": codigo_colecao.lower(), "collector_number": numero_carta}]
            dados = buscar_detalhes_em_lote(identificador)
            if dados:
                carta = dados[0]
                cotacao = get_usd_to_brl()
                preco_usd = float(carta.get("prices", {}).get("usd") or 0)
                preco_foil = float(carta.get("prices", {}).get("usd_foil") or 0)
                preco_brl = round(preco_usd * cotacao, 2)
                preco_brl_foil = round(preco_foil * cotacao, 2)
                imagem = carta.get("image_uris", {}).get("normal")

                nova = pd.DataFrame([{
                    "nome": carta.get("name"),
                    "tipo": carta.get("type_line"),
                    "preco_brl": preco_brl,
                    "preco_brl_foil": preco_brl_foil,
                    "padrao": padrao,
                    "foil": foil,
                    "imagem": imagem,
                    "colecao": codigo_colecao.lower(),
                    "numero": numero_carta,
                    "colecao_nome": carta.get("set_name"),
                    "icone_colecao": carta.get("set_icon_svg_uri"),
                    "raridade": carta.get("rarity"),
                    "cores": ", ".join(carta.get("colors", [])),
                    "mana_cost": carta.get("mana_cost"),
                    "nome_2": None
                }])
                try:
                    df_existente = pd.read_csv(CSV_PATH)
                    df_final = pd.concat([df_existente, nova], ignore_index=True)
                except:
                    df_final = nova

                sucesso = salvar_csv_em_github(df_final, REPO, CSV_PATH, GITHUB_TOKEN)
                if sucesso:
                    st.success("Card add!")
                else:
                    st.error("Error.")
            else:
                st.error("Card not found in API.")
    else:
        with st.form("form_carta"):
            nome = st.text_input("Card name")
            tipo = st.text_input("Type")
            preco_brl = st.number_input("Price (BRL)", min_value=0.0)
            preco_brl_foil = st.number_input("Price Foil (BRL)", min_value=0.0)
            padrao = st.number_input("Regular quantity", min_value=0)
            foil = st.number_input("Foil quantity", min_value=0)
            imagem = st.text_input("Image URL")
            colecao = st.text_input("Collection code")
            numero = st.text_input("Card number")
            colecao_nome = st.text_input("Collection name")
            icone_colecao = st.text_input("Collection icon URL")
            raridade = st.selectbox("Rarity", ["common", "uncommon", "rare", "mythic"])
            cores = st.text_input("Colors (ex: W, U, B, R, G, C, L)")
            mana_cost = st.text_input("Mana cost (ex: {1}{G}{G})")
            nome_2 = st.text_input("Alternative name or secundary face (optional)")
            enviado = st.form_submit_button("Add card")

        if enviado:
            nova_carta = pd.DataFrame([{
                "nome": nome, "tipo": tipo, "preco_brl": preco_brl, "preco_brl_foil": preco_brl_foil,
                "padrao": padrao, "foil": foil, "imagem": imagem, "colecao": colecao,
                "numero": numero, "colecao_nome": colecao_nome, "icone_colecao": icone_colecao,
                "raridade": raridade, "cores": cores, "mana_cost": mana_cost, "nome_2": nome_2
            }])
            try:
                df_existente = pd.read_csv(CSV_PATH)
                df_final = pd.concat([df_existente, nova_carta], ignore_index=True)
            except:
                df_final = nova_carta

            sucesso, mensagem = salvar_csv_em_github(df_final, REPO, CSV_PATH, GITHUB_TOKEN)

            if sucesso:
                st.success("Cards add!")
            else:
                st.error(f"Erro ao salvar no GitHub: {mensagem}")

with aba4:
    st.header("Import cards using Excel")

    arquivo = st.file_uploader("Select the excel file", type=["xlsx"])
    if arquivo:
        df = pd.read_excel(arquivo)
        df = df.dropna(subset=["colecao", "numero"])
        df["colecao"] = df["colecao"].astype(str).str.lower()
        df["numero"] = df["numero"].astype(str)
        df["padrao"] = df.get("padrao", 1)
        df["foil"] = df.get("foil", 0)

        df = df.groupby(["colecao", "numero"], as_index=False).agg({
            "padrao": "sum",
            "foil": "sum",
            **{col: "first" for col in df.columns if col not in ["colecao", "numero", "padrao", "foil"]}
        })

        cotacao = get_usd_to_brl()
        identificadores = [{"set": row["colecao"], "collector_number": row["numero"]} for _, row in df.iterrows()]
        todos_detalhes = []
        for lote in dividir_em_lotes(identificadores, 75):
            todos_detalhes.extend(buscar_detalhes_em_lote(lote))
            time.sleep(0.5)

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

        df_final = pd.concat([df, df_detalhes], axis=1)
        sucesso, mensagem = salvar_csv_em_github(df_final, REPO, CSV_PATH, GITHUB_TOKEN)

        if sucesso:
            st.success("Cards add!")
        else:
            st.error(f"Erro ao salvar no GitHub: {mensagem}")

with aba5:
    st.header("Card Manager")

try:
    df = pd.read_csv(CSV_PATH)

    # Converte colunas numéricas com segurança
    df["padrao"] = pd.to_numeric(df["padrao"], errors="coerce").fillna(0).astype(int)
    df["foil"] = pd.to_numeric(df["foil"], errors="coerce").fillna(0).astype(int)

    # Editor completo
    df_editado = st.data_editor(
        df,
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
