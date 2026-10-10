import os
import json
import requests
from bs4 import BeautifulSoup

# --- CONFIGURAÇÕES DO TELEGRAM ---
# Dica: O ideal é guardar isso como Secrets do GitHub, mas se preferir, pode colocar direto aqui:
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8900930532:AAGHQOqiXJJgOA1Gppxxetjbv9URQ_g17Lw
")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "6682065062")

ARQUIVO_VISTAS = "vagas_vistas.json"

def carregar_vagas_vistas():
    if os.path.exists(ARQUIVO_VISTAS):
        try:
            with open(ARQUIVO_VISTAS, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def salvar_vagas_vistas(vistas):
    with open(ARQUIVO_VISTAS, "w", encoding="utf-8") as f:
        json.dump(vistas, f, ensure_ascii=False, indent=4)

def enviar_mensagem_telegram(mensagem):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensagem,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload)
        return response.status_code == 200
    except Exception as e:
        print(f"Erro ao enviar mensagem para o Telegram: {e}")
        return False

def buscar_vagas_olx():
    vagas = []
    # URL de busca da OLX para diarista (exemplo região de São Paulo / ajuste se precisar)
    url = "https://www.olx.com.br/brasil?q=diarista"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(f"Erro ao acessar OLX: Status {response.status_code}")
            return vagas
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # O seletor da OLX pode variar, buscamos os cards de anúncios padrão
        anuncios = soup.find_all('a', href=True)
        
        for anuncio in anuncios:
            href = anuncio.get('href')
            # Filtra links que parecem ser anúncios de produtos/vagas da OLX
            if href and "/vi/" in href:
                titulo = anuncio.get_text().strip()
                if titulo and len(titulo) > 10:
                    link = href if href.startswith("http") else f"https://www.olx.com.br{href}"
                    vagas.append({
                        "id": link,
                        "titulo": f"🧹 [OLX] {titulo}",
                        "link": link
                    })
    except Exception as e:
        print(f"Erro no scraper da OLX: {e}")
        
    return vagas

def buscar_vagas_indeed():
    vagas = []
    # URL de busca do Indeed para diarista/limpeza
    url = "https://br.indeed.com/jobs?q=diarista&l=Brasil"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(f"Erro ao acessar Indeed: Status {response.status_code}")
            return vagas
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Buscando cards de vagas no Indeed
        for card in soup.find_all('div', class_='job_seen_beacon'):
            titulo_tag = card.find('h2', class_='jobTitle')
            link_tag = card.find('a', href=True)
            
            if titulo_tag and link_tag:
                titulo = titulo_tag.get_text().strip()
                link = "https://br.indeed.com" + link_tag['href'] if not link_tag['href'].startswith("http") else link_tag['href']
                
                vagas.append({
                    "id": link,
                    "titulo": f"💼 [Indeed] {titulo}",
                    "link": link
                })
    except Exception as e:
        print(f"Erro no scraper do Indeed: {e}")
        
    return vagas

def main():
    print("Iniciando varredura de vagas (OLX + Indeed)...")
    vistas = carregar_vagas_vistas()
    novas_vistas = list(vistas)
    
    # Coleta de todas as fontes
    todas_vagas = buscar_vagas_olx() + buscar_vagas_indeed()
    
    contador_novas = 0
    for vaga in todas_vagas:
        vaga_id = vaga["id"]
        if vaga_id not in vistas:
            # Envia alerta no Telegram
            mensagem = f"*{vaga['titulo']}*\n\n🔗 [Acessar Vaga]({vaga['link']})"
            sucesso = enviar_mensagem_telegram(mensagem)
            
            if sucesso:
                novas_vistas.append(vaga_id)
                contador_novas += 1
                
    salvar_vagas_vistas(novas_vistas)
    print(f"Varredura concluída. {contador_novas} novas vagas encontradas e enviadas.")

if __name__ == "__main__":
    main()
