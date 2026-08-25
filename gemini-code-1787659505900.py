import json
import re
from datetime import datetime
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://camaramorrinhos.ce.gov.br"
# Endpoint de listagem de matérias/proposituras (ajuste o path conforme a URL exata do portal)
LISTA_URL = f"{BASE_URL}/materia-legislativa"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}

def extrair_detalhes_materia(link_materia):
    """Acessa a página individual da matéria para extrair a tramitação detalhada."""
    try:
        resp = requests.get(link_materia, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return []
        soup = BeautifulSoup(resp.content, "html.parser")
        
        historico = []
        # Procura tabelas ou blocos de tramitação/histórico no HTML
        tabela_tramitacao = soup.select("table.table-tramitacao tr, .historico-tramitacao-item")
        for row in tabela_tramitacao:
            colunas = [c.get_text(strip=True) for c in row.find_all(["td", "div"])]
            if len(colunas) >= 2:
                historico.append({
                    "data": colunas[0],
                    "despacho": colunas[1],
                    "unidade": colunas[2] if len(colunas) > 2 else "Plenário"
                })
        return historico
    except Exception as e:
        print(f"Erro ao extrair detalhes de {link_materia}: {e}")
        return []

def coletar_todas_materias():
    materias = []
    pagina = 1

    while True:
        url = f"{LISTA_URL}?pagina={pagina}"
        print(f"Buscando página {pagina}...")
        
        try:
            resp = requests.get(url, headers=HEADERS, timeout=20)
            if resp.status_code != 200:
                break
            
            soup = BeautifulSoup(resp.content, "html.parser")
            
            # Localiza os cards/linhas das matérias
            itens = soup.select(".card-materia, .item-propositura, tr.linha-materia")
            if not itens:
                # Se não encontrar itens, encerra a paginação
                break
                
            for item in itens:
                titulo_el = item.select_one("a.titulo, h3 a, .numero-materia")
                if not titulo_el:
                    continue
                
                titulo = titulo_el.get_text(strip=True)
                link = titulo_el.get("href", "")
                if link and not link.startswith("http"):
                    link = BASE_URL + link
                
                ementa_el = item.select_one(".ementa, .descricao, p.resumo")
                ementa = ementa_el.get_text(strip=True) if ementa_el else "Sem ementa disponível"
                
                autor_el = item.select_one(".autor, .vereador")
                autor = autor_el.get_text(strip=True) if autor_el else "Não informado"
                
                status_el = item.select_one(".status, .badge-status, .badge")
                status = status_el.get_text(strip=True) if status_el else "Em tramitação"
                
                data_el = item.select_one(".data, .data-publicacao")
                data_pub = data_el.get_text(strip=True) if data_el else ""

                # Identificador único (número/ano ou hash do link)
                id_match = re.search(r"(\d+[\/\-]\d{4})", titulo)
                mat_id = id_match.group(1) if id_match else link

                materia_obj = {
                    "id": mat_id,
                    "titulo": titulo,
                    "ementa": ementa,
                    "autor": autor,
                    "status": status,
                    "data": data_pub,
                    "link_original": link,
                    "tramitacoes": extrair_detalhes_materia(link) if link else []
                }
                materias.append(materia_obj)
            
            pagina += 1
            if pagina > 10:  # Limite de segurança para testes iniciais
                break
                
        except Exception as e:
            print(f"Erro na página {pagina}: {e}")
            break

    # Salva o resultado consolidado
    payload = {
        "ultima_atualizacao": datetime.now().strftime("%d/%m/%Y às %H:%M:%S"),
        "total": len(materias),
        "materias": materias
    }
    
    with open("dados_materias.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    
    print(f"Coleta finalizada com sucesso: {len(materias)} matérias salvas.")

if __name__ == "__main__":
    coletar_todas_materias()