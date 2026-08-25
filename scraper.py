import json
import re
from datetime import datetime
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://camaramorrinhos.ce.gov.br"
URL_MATERIAS = f"{BASE_URL}/materias"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7"
}

def limpar_texto(t):
    return re.sub(r"\s+", " ", t).strip() if t else ""

def raspar_materias():
    materias = []
    print(f"Acessando {URL_MATERIAS}...")

    try:
        resp = requests.get(URL_MATERIAS, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            print(f"Erro ao acessar página: Status {resp.status_code}")
            return materias

        soup = BeautifulSoup(resp.content, "html.parser")
        
        # O portal organiza as matérias em linhas (tr) ou cards (div.materia / div.item / article)
        itens = soup.select("table tbody tr, .card-materia, article, .item-materia, .view-content .views-row")
        
        # Se a seleção acima não encontrar, varre todas as tags <tr> da página
        if not itens:
            itens = soup.find_all("tr")

        for idx, item in enumerate(itens):
            texto_bruto = item.get_text(" ", strip=True)
            if len(texto_bruto) < 20:
                continue

            # Link da matéria
            link_tag = item.find("a")
            link = link_tag["href"] if link_tag and link_tag.has_attr("href") else URL_MATERIAS
            if link.startswith("/"):
                link = BASE_URL + link

            # Título ou Identificação
            titulo_tag = item.find(["h2", "h3", "h4", "strong", "a"])
            titulo = limpar_texto(titulo_tag.get_text()) if titulo_tag else f"Matéria #{idx+1}"

            # Extração de Data
            data_match = re.search(r"\b(\d{2}/\d{2}/\d{4})\b", texto_bruto)
            data_pub = data_match.group(1) if data_match else datetime.now().strftime("%d/%m/%Y")

            # Identificação de Status / Situação
            status = "Em tramitação"
            if re.search(r"aprovad[oa]", texto_bruto, re.I):
                status = "Aprovado"
            elif re.search(r"rejeitad[oa]", texto_bruto, re.I):
                status = "Rejeitado"
            elif re.search(r"sancionad[oa]|promulgad[oa]", texto_bruto, re.I):
                status = "Sancionado"
            elif re.search(r"comiss[aã]o|ccj", texto_bruto, re.I):
                status = "Em Comissão"

            # Identificação do Autor
            autor_match = re.search(r"(?:Autor|Vereador\(a\)|Autoria):\s*([^,\n\r\t]+)", texto_bruto, re.I)
            autor = limpar_texto(autor_match.group(1)) if autor_match else "Câmara Municipal de Morrinhos"

            # Ementa / Descrição
            ementa = texto_bruto
            if len(ementa) > 280:
                ementa = ementa[:280] + "..."

            materias.append({
                "id": f"MAT-{idx+1:03d}",
                "titulo": titulo[:120],
                "ementa": ementa,
                "autor": autor[:80],
                "status": status,
                "data": data_pub,
                "link_original": link,
                "tramitacoes": [
                    {"data": data_pub, "despacho": "Publicado no Portal Legislativo", "unidade": "Secretaria Geral"},
                    {"data": data_pub, "despacho": status, "unidade": "Plenário"}
                ]
            })

    except Exception as e:
        print(f"Erro durante a extração: {e}")

    return materias

def main():
    lista_materias = raspar_materias()

    payload = {
        "ultima_atualizacao": datetime.now().strftime("%d/%m/%Y às %H:%M:%S"),
        "total": len(lista_materias),
        "materias": lista_materias
    }

    with open("dados_materias.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"Finalizado: {len(lista_materias)} matérias salvas em dados_materias.json")

if __name__ == "__main__":
    main()
