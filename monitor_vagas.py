from datetime import datetime
import json
import os
import pytz
import requests
from bs4 import BeautifulSoup

# --- CONFIGURAÇÕES DO TELEGRAM ---
# Usando as variáveis de ambiente com segurança (vindas do GitHub Secrets)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

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
  if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
    print("Erro: TELEGRAM_TOKEN ou TELEGRAM_CHAT_ID não configurados.")
    return False

  url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
  payload = {
      "chat_id": TELEGRAM_CHAT_ID,
      "text": mensagem,
      "parse_mode": "Markdown",
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
  headers = {
      "User-Agent": (
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
          " like Gecko) Chrome/120.0.0.0 Safari/537.36"
      )
  }

  try:
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
      print(f"Erro ao acessar OLX: Status {response.status_code}")
      return vagas

    soup = BeautifulSoup(response.text, "html.parser")
    anuncios = soup.find_all("a", href=True)

    for anuncio in anuncios:
      href = anuncio.get("href")
      if href and "/vi/" in href:
        titulo = anuncio.get_text().strip()
        if titulo and len(titulo) > 10:
          link = (
              href
              if href.startswith("http")
              else f"https://www.olx.com.br{href}"
          )
          vagas.append({
              "id": link,
              "titulo": f"🧹 [OLX] {titulo}",
              "link": link,
          })
  except Exception as e:
    print(f"Erro no scraper da OLX: {e}")

  return vagas


def buscar_vagas_indeed():
  vagas = []
  url = "https://br.indeed.com/jobs?q=diarista&l=Brasil"
  headers = {
      "User-Agent": (
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
          " like Gecko) Chrome/120.0.0.0 Safari/537.36"
      )
  }

  try:
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
      print(f"Erro ao acessar Indeed: Status {response.status_code}")
      return vagas

    soup = BeautifulSoup(response.text, "html.parser")

    for card in soup.find_all("div", class_="job_seen_beacon"):
      titulo_tag = card.find("h2", class_="jobTitle")
      link_tag = card.find("a", href=True)

      if titulo_tag and link_tag:
        titulo = titulo_tag.get_text().strip()
        link = (
            "https://br.indeed.com" + link_tag["href"]
            if not link_tag["href"].startswith("http")
            else link_tag["href"]
        )

        vagas.append(
            {"id": link, "titulo": f"💼 [Indeed] {titulo}", "link": link}
        )
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
      # Envia alerta individual da nova vaga no Telegram
      mensagem = f"*{vaga['titulo']}*\n\n🔗 [Acessar Vaga]({vaga['link']})"
      sucesso = enviar_mensagem_telegram(mensagem)

      if sucesso:
        novas_vistas.append(vaga_id)
        contador_novas += 1

  salvar_vagas_vistas(novas_vistas)

  # --- ENVIAR STATUS / HEARTBBEAT (SINAL DE VIDA) ---
  try:
    fuso_br = pytz.timezone("America/Sao_Paulo")
    data_hora_atual = datetime.now(fuso_br).strftime("%d/%m/%Y %H:%M")
  except Exception:
    data_hora_atual = datetime.now().strftime("%d/%m/%Y %H:%M")

  total_analisadas = len(todas_vagas)

  mensagem_status = (
      "🤖 *Status do Monitor de Vagas*\n"
      f"🕒 *Rodou em:* {data_hora_atual}\n"
      f"🔎 *Vagas analisadas:* {total_analisadas}\n"
      f"🆕 *Novas enviadas:* {contador_novas}\n"
      "🟢 *Status:* Tudo certo e monitorando!"
  )

  enviar_mensagem_telegram(mensagem_status)
  print(
      f"Varredura concluída. {contador_novas} novas vagas encontradas e"
      " enviadas."
  )


if __name__ == "__main__":
  main()
