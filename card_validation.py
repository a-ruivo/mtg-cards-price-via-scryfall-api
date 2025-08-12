# Validando cartas na api
import requests

def buscar_por_set_e_numero(set_code, collector_number):
    url = f"https://api.scryfall.com/cards/{set_code}/{collector_number}"
    response = requests.get(url)

    if response.status_code == 200:
        carta = response.json()
        print(f"Nome: {carta['name']}")
    else:
        print(f"Carta {set_code.upper()} #{collector_number} não encontrada.")

# Exemplo de uso
buscar_por_set_e_numero("blb","2")