import pandas as pd
import requests
import time

# Carregar o Excel
df = pd.read_excel("cartas_magic.xlsx")
df = df.dropna(subset=["colecao", "numero"])
df["colecao"] = df["colecao"].astype(str).str.lower()

# Carregar o Excel
df = pd.read_excel("cartas_magic.xlsx")
df = df.dropna(subset=["colecao", "numero"])
df["colecao"] = df["colecao"].astype(str).str.lower()
df["numero"] = df["numero"].astype(str)

# Preencher valores padrão se não existirem
if "padrao" not in df.columns:
    df["padrao"] = 1
if "foil" not in df.columns:
    df["foil"] = 0

# Consolidar duplicatas somando padrao e foil, mantendo outras colunas
df = df.groupby(["colecao", "numero"], as_index=False).agg({
    "padrao": "sum",
    "foil": "sum",
    **{col: "first" for col in df.columns if col not in ["colecao", "numero", "padrao", "foil"]}
})

# Calcular total de cópias e valor estimado em BRL (será preenchido depois)
df["total_copias"] = df["padrao"] + df["foil"]

# Preparar lista de identificadores
identificadores = [
    {"set": linha["colecao"], "collector_number": str(linha["numero"])}
    for _, linha in df.iterrows()
]

# Função para dividir em lotes
def dividir_em_lotes(lista, tamanho_lote):
    for i in range(0, len(lista), tamanho_lote):
        yield lista[i:i + tamanho_lote]

# Função para buscar dados em lote
def buscar_detalhes_em_lote(identificadores):
    url = "https://api.scryfall.com/cards/collection"
    payload = {"identifiers": identificadores}
    resposta = requests.post(url, json=payload)
    if resposta.status_code == 200:
        return resposta.json()["data"]
    else:
        print("Erro:", resposta.status_code)
        return []

# Função para obter cotação do dólar
def get_usd_to_brl():
    try:
        response = requests.get("https://economia.awesomeapi.com.br/json/last/USD-BRL")
        data = response.json()
        return float(data["USDBRL"]["bid"])
    except Exception as e:
        print("Erro ao obter cotação:", e)
        return 5.0  # fallback

# Obter cotação
cotacao_usd_brl = get_usd_to_brl()

# Processar todos os lotes
todos_detalhes = []
lotes = list(dividir_em_lotes(identificadores, 75))
print(f"Total de lotes: {len(lotes)}")

for i, lote in enumerate(lotes, start=1):
    print(f"Processando lote {i}/{len(lotes)}...")
    dados = buscar_detalhes_em_lote(lote)
    todos_detalhes.extend(dados)
    time.sleep(0.5)

# Montar dicionário com os dados
# Montar dicionário com os dados
detalhes_dict = {}
for carta in todos_detalhes:
    preco_usd = float(carta.get("prices", {}).get("usd") or 0)
    preco_usd_foil = float(carta.get("prices", {}).get("usd_foil") or 0)

    faces = carta.get("card_faces")
    printed_faces = carta.get("printed_card_faces", [])

    # Função auxiliar para buscar imagem
    def buscar_imagem(face_index):
        return (
            (faces[face_index].get("image_uris", {}).get("normal") if faces and len(faces) > face_index else None)
            or (printed_faces[face_index].get("image_uris", {}).get("normal") if len(printed_faces) > face_index else None)
            or carta.get("image_uris", {}).get("normal")
        )

    if faces:
        face1 = faces[0]
        face2 = faces[1] if len(faces) > 1 else {}

        detalhes_dict[(carta["set"], carta["collector_number"])] = {
            "nome": face1.get("name"),
            "mana_cost": face1.get("mana_cost"),
            "cores": ", ".join(face1.get("colors", [])),
            "cmc": carta.get("cmc"),
            "descricao": face1.get("oracle_text"),
            "power": face1.get("power"),
            "toughness": face1.get("toughness"),
            "imagem": buscar_imagem(0),

            "nome_2": face2.get("name"),
            "mana_cost_2": face2.get("mana_cost"),
            "cores_2": ", ".join(face2.get("colors", [])),
            "descricao_2": face2.get("oracle_text"),
            "power_2": face2.get("power"),
            "toughness_2": face2.get("toughness"),
            "imagem_2": buscar_imagem(1),

            "colecao_nome": carta.get("set_name"),
            "icone_colecao": carta.get("set_icon_svg_uri"),
            "data_lancamento": carta.get("released_at"),
            "raridade": carta.get("rarity"),
            "tipo": carta.get("type_line"),
            "preco_usd": preco_usd,
            "preco_brl": round(preco_usd * cotacao_usd_brl, 2),
            "preco_usd_foil": preco_usd_foil,
            "preco_brl_foil": round(preco_usd_foil * cotacao_usd_brl, 2)
        }
    else:
        detalhes_dict[(carta["set"], carta["collector_number"])] = {
            "nome": carta.get("name"),
            "mana_cost": carta.get("mana_cost"),
            "cores": ", ".join(carta.get("colors", [])),
            "cmc": carta.get("cmc"),
            "descricao": carta.get("oracle_text"),
            "power": carta.get("power"),
            "toughness": carta.get("toughness"),
            "imagem": buscar_imagem(0),

            "nome_2": None,
            "mana_cost_2": None,
            "cores_2": None,
            "descricao_2": None,
            "power_2": None,
            "toughness_2": None,
            "imagem_2": None,

            "colecao_nome": carta.get("set_name"),
            "icone_colecao": carta.get("set_icon_svg_uri"),
            "data_lancamento": carta.get("released_at"),
            "raridade": carta.get("rarity"),
            "tipo": carta.get("type_line"),
            "preco_usd": preco_usd,
            "preco_brl": round(preco_usd * cotacao_usd_brl, 2),
            "preco_usd_foil": preco_usd_foil,
            "preco_brl_foil": round(preco_usd_foil * cotacao_usd_brl, 2)
        }

# Lista de chaves esperadas
chaves_detalhes = [
    "nome", "mana_cost", "cores", "cmc", "descricao", "power", "toughness", "imagem",
    "nome_2", "mana_cost_2", "cores_2", "descricao_2", "power_2", "toughness_2", "imagem_2",
    "colecao_nome", "icone_colecao", "data_lancamento", "raridade", "tipo",
    "preco_usd", "preco_brl", "preco_usd_foil", "preco_brl_foil"
]

# Adicionar colunas ao DataFrame
df_detalhes = df.apply(
    lambda linha: pd.Series(
        detalhes_dict.get(
            (linha["colecao"], str(linha["numero"])),
            {chave: None for chave in chaves_detalhes}
        )
    ),
    axis=1
)

df_final = pd.concat([df, df_detalhes], axis=1)

# Salvar em Excel e CSV
import os

arquivo_csv = "cartas_magic_detalhadas.csv"
arquivo_xlsx = "cartas_magic_detalhadas.xlsx"

# Verificar se já existe
if os.path.exists(arquivo_csv):
    df_existente = pd.read_csv(arquivo_csv)
    df_final = pd.concat([df_existente, df_final], ignore_index=True)

    # Remover duplicatas com base em colecao + numero
    df_final["numero"] = df_final["numero"].astype(str)
    df_final["colecao"] = df_final["colecao"].astype(str).str.lower()
    df_final = df_final.groupby(["colecao", "numero"], as_index=False).agg({
        "padrao": "sum",
        "foil": "sum",
        **{col: "first" for col in df_final.columns if col not in ["colecao", "numero", "padrao", "foil"]}
    })

df_final.to_excel(arquivo_xlsx, index=False)
df_final.to_csv(arquivo_csv, index=False)
print("Arquivos final gerados com sucesso: XLSX e CSV!")
