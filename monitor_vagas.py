import requests
from bs4 import BeautifulSoup
import time
import json
import os

# ==========================================
# CONFIGURAÇÕES DO TELEGRAM E DA BUSCA
# ==========================================
TELEGRAM_TOKEN = "8900930532:AAGHQOqiXJJgOA1Gppxxetjbv9URQ_g17Lw"
"
TELEGRAM_CHAT_ID = "6682065062"

# URL da busca na OLX (Exemplo: São Paulo e região - Vagas de Emprego)
# Você pode alterar o termo 'diarista' ou a região ajustando a URL abaixo:
URL_BUSCA = "https://www.olx.com.br/vagas-de-emprego?q=diarista"

# Arquivo local para salvar as vagas já enviadas e evitar alertas repetidos
ARQUIVO_VAGAS_VISTAS = "vagas_vistas.json"

# Headers para simular um navegador comum e evitar bloqueios na requisição
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
    'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7'
}

# ==========================================
# FUNÇÕES DO SISTEMA
# ==========================================

def carregar_vagas_vistas():
    """Carrega a lista de IDs/links de vagas já notificadas."""
    if os.path.exists(ARQUIVO_VAGAS_VISTAS):
        with open(ARQUIVO_VAGAS_VISTAS, 'r', encoding='utf-8') as f:
            return set(json.load(f))
    return set()

def salvar_vagas_vistas(vagas_vistas):
    """Salva a lista atualizada de vagas notificadas num arquivo JSON."""
    with open(ARQUIVO_VAGAS_VISTAS, 'w', encoding='utf-8') as f:
        json.dump(list(vagas_vistas), f, ensure_ascii=False, indent=2)

def enviar_mensagem_telegram(mensagem):
    """Envia uma mensagem formatada para o seu Telegram via API."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensagem,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"Erro ao enviar mensagem no Telegram: {e}")
        return False

def buscar_vagas_olx():
    """Realiza o scraping dos anúncios na OLX e retorna uma lista de vagas encontradas."""
    print(" Buscando novas vagas...")
    vagas = []
    
    try:
        response = requests.get(URL_BUSCA, headers=HEADERS, timeout=15)
        if response.status_code != 200:
            print(f"Erro na requisição. Código: {response.status_code}")
            return vagas

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Seleciona os cards de anúncio na OLX (seletores baseados na estrutura HTML atual da OLX)
        anuncios = soup.find_all('section', {'data-olx-element': 'ad-card'})
        
        if not anuncios:
            # Estrutura alternativa caso a tag principal varie
            anuncios = soup.find_all('div', class_=lambda c: c and 'ad-card' in c)

        for anuncio in anuncios:
            link_tag = anuncio.find('a')
            if not link_tag or not link_tag.get('href'):
                continue
                
            link = link_tag['href']
            
            # Captura o título da vaga
            titulo_tag = anuncio.find('h2') or anuncio.find('h3')
            titulo = titulo_tag.text.strip() if titulo_tag else "Vaga de Diarista / Limpeza"
            
            # Captura a localização, se disponível
            local_tag = anuncio.find('span', class_=lambda c: c and 'location' in c)
            localizacao = local_tag.text.strip() if local_tag else "Região não especificada"

            vagas.append({
                'id': link,  # Usando o próprio link como identificador único
                'titulo': titulo,
                'localizacao': localizacao,
                'link': link
            })
            
    except Exception as e:
        print(f"Erro ao buscar vagas: {e}")
        
    return vagas

def executar_monitoramento():
    """Função principal que integra a busca, filtragem e envio dos alertas."""
    vagas_vistas = carregar_vagas_vistas()
    vagas_encontradas = buscar_vagas_olx()
    novas_vagas_cont = 0

    for vaga in vagas_encontradas:
        if vaga['id'] not in vagas_vistas:
            # Formata a mensagem para o Telegram
            mensagem = (
                f"🚨 *NOVA VAGA ENCONTRADA!*\n\n"
                f"📌 *Título:* {vaga['titulo']}\n"
                f"📍 *Local:* {vaga['localizacao']}\n\n"
                f"🔗 [Clique aqui para abrir o anúncio]({vaga['link']})"
            )
            
            if enviar_mensagem_telegram(mensagem):
                print(f" Alerta enviado: {vaga['titulo']}")
                vagas_vistas.add(vaga['id'])
                novas_vagas_cont += 1
                time.sleep(2)  # Pausa breve entre envios para evitar flood

    salvar_vagas_vistas(vagas_vistas)
    print(f"Busca concluída. {novas_vagas_cont} novas vagas enviadas.")

# ==========================================
# EXECUÇÃO ÚNICA (Para rodar via agendador na nuvem)
# ==========================================
if __name__ == "__main__":
    print("🤖 Iniciando verificação de vagas...")
    executar_monitoramento()
    print(" Fim da verificação.")