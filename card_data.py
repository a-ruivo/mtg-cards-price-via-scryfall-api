import pandas as pd
import requests
import time

# Carregar o Excel
df = pd.read_excel("cartas_magic.xlsx")
df = df.dropna(subset=["colecao", "numero"])
df["colecao"] = df["colecao"].astype(str).str.lower()

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
        return None

# Obter cotação antes de processar os dados
cotacao_usd_brl = get_usd_to_brl()
if cotacao_usd_brl is None:
    cotacao_usd_brl = 5.0  # fallback

# Processar todos os lotes com feedback
todos_detalhes = []
lotes = list(dividir_em_lotes(identificadores, 75))
print(f"Total de lotes: {len(lotes)}")

for i, lote in enumerate(lotes, start=1):
    print(f"Processando lote {i}/{len(lotes)}...")
    dados = buscar_detalhes_em_lote(lote)
    todos_detalhes.extend(dados)
    time.sleep(0.5)

# Montar dicionário com os dados
detalhes_dict = {
    (carta["set"], carta["collector_number"]): {
        "nome": carta.get("name"),
        "mana_cost": carta.get("mana_cost"),
        "cores": ", ".join(carta.get("colors", [])),
        "cmc": carta.get("cmc"),
        "descricao": carta.get("oracle_text"),
        "power": carta.get("power"),
        "toughness": carta.get("toughness"),
        "imagem": carta.get("image_uris", {}).get("normal"),
        "colecao_nome": carta.get("set_name"),
        "data_lancamento": carta.get("released_at"),
        "raridade": carta.get("rarity"),
        "preco_usd": carta.get("prices", {}).get("usd"),
        "preco_brl": round(float(carta.get("prices", {}).get("usd") or 0) * cotacao_usd_brl, 2),
        "preco_usd_foil": carta.get("prices", {}).get("usd_foil"),
        "preco_brl_foil": round(float(carta.get("prices", {}).get("usd_foil") or 0) * cotacao_usd_brl, 2)
    }
    for carta in todos_detalhes
}

# Adicionar colunas ao DataFrame
df_detalhes = df.apply(
    lambda linha: pd.Series(
        detalhes_dict.get(
            (linha["colecao"], str(linha["numero"])),
            {chave: None for chave in [
                "nome", "mana_cost", "cores", "cmc", "descricao", "power", "toughness",
                "imagem", "colecao_nome", "data_lancamento", "raridade",
                "preco_usd", "preco_brl", "preco_usd_foil", "preco_brl_foil"
            ]}
        )
    ),
    axis=1
)

df_final = pd.concat([df, df_detalhes], axis=1)
df_final.to_excel("cartas_magic_detalhadas.xlsx", index=False)
print("Arquivo final gerado com sucesso!")
