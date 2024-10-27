
import json


def order_json():
    # Abrir e ler o arquivo data.json
    with open('data.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Ordenar a lista de dicionários pelo campo 'date' e 'product'
    data.sort(key=lambda x: x['date'], reverse=True)

    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)





if __name__ == '__main__':
    order_json()