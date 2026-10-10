from datetime import datetime, timezone, timedelta
import json
import os
import requests
from bs4 import BeautifulSoup

# --- CONFIGURAÇÕES DO TELEGRAM ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

ARQUIVO_VISTAS = "vagas_vistas.json"

# Cabeçalhos robustos para simular um navegador real e evitar bloqueios básicos
HEADERS_GLOBAL = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://www.google.com/"
}

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
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Erro: TELEGRAM_TOKEN ou TELEGRAM_CHAT_ID não configurados.")
        return False
        
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
    url = "https://www.olx.com.br/brasil?q=diarista"
    
    try:
        response = requests.get(url, headers=HEADERS_GLOBAL, timeout=10)
        print(f"OLX Status Code: {response.status_code}")
        
        if response.status_code != 200:
            return vagas
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Procura por links de anúncios na OLX de forma mais abrangente
        anuncios = soup.find_all('a', href=True)
        
        for anuncio in anuncios:
            href = anuncio.get('href')
            if href and ("/vi/" in href or "olx.com.br/" in href) and "q=" not in href:
                titulo = anuncio.get_text().strip()
                if titulo and len(titulo) > 12: # Filtra títulos muito curtos
                    link = href if href.startswith("http") else f"https://www.olx.com.br{href}"
                    # Evita duplicadas na mesma execução
                    if not any(v['link'] == link for v in vagas):
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
    url = "https://br.indeed.com/jobs?q=diarista&l=Brasil"
    
    try:
        response = requests.get(url, headers=HEADERS_GLOBAL, timeout=10)
        print(f"Indeed Status Code: {response.status_code}")
        
        if response.status_code != 200:
            return vagas
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Busca cards de vagas do Indeed (tentando múltiplas classes comuns)
        cards = soup.find_all('div', class_=lambda x: x and ('job_seen_beacon' in x or 'card' in x or 'slider_item' in x))
        if not cards:
            cards = soup.find_all('td', class_='resultContent')
            
        for card in cards:
            titulo_tag = card.find('h2', class_=lambda x: x and 'jobTitle' in x) or card.find('a')
            link_tag = card.find('a', href=True)
            
            if titulo_tag and link_tag:
                titulo = titulo_tag.get_text().strip()
                href = link_tag['href']
                link = "https://br.indeed.com" + href if not href.startswith("http") else href
                
                if not any(v['link'] == link for v in vagas):
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
    print(f"Total de vagas brutas encontradas: {len(todas_vagas)}")
    
    contador_novas = 0
    for vaga in todas_vagas:
        vaga_id = vaga["id"]
        if vaga_id not in vistas:
            # Envia alerta individual da nova vaga no Telegram
            mensagem = f"*{vaga['titulo']}*\n\n🔗 [Acessar Vaga]({vaga['link']})"
            sucesso = enviar_mensagem_telegram(mensagem)
            
            if sucesso:
                novas_vistas.append(vaga_id)
                contador_novas += 1
                
    salvar_vagas_vistas(novas_vistas)
    
    # --- ENVIAR STATUS / HEARTBEAT (SINAL DE VIDA) ---
    try:
        fuso_br = timezone(timedelta(hours=-3))
        data_hora_atual = datetime.now(fuso_br).strftime('%d/%m/%Y %H:%M')
    except Exception:
        data_hora_atual = datetime.now().strftime('%d/%m/%Y %H:%M')
        
    total_analisadas = len(todas_vagas)
    
    mensagem_status = (
        "🤖 *Status do Monitor de Vagas*\n"
        f"🕒 *Rodou em:* {data_hora_atual}\n"
        f"🔎 *Vagas analisadas:* {total_analisadas}\n"
        f"🆕 *Novas enviadas:* {contador_novas}\n"
        "🟢 *Status:* Tudo certo e monitorando!"
    )
    
    enviar_mensagem_telegram(mensagem_status)
    print(f"Varredura concluída. {contador_novas} novas vagas encontradas e enviadas.")

if __name__ == "__main__":
    main()
