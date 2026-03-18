import scrapetube
import urllib.parse
import aiohttp
import asyncio
import requests
import re
import os
import itertools
import csv
import json
import argparse
import threading
from datetime import datetime

# Cores e Estética
G = "\033[92m"  # Verde (Sucesso)
R = "\033[91m"  # Vermelho (Alerta)
Y = "\033[93m"  # Amarelo (Aviso)
C = "\033[96m"  # Ciano (Info)
B = "\033[1m"   # Bold (Destaque)
W = "\033[0m"   # White (Reset)

game_rating_cache = {}
dict_lock = threading.Lock()

# Lista local estendida: inclui títulos completos, siglas e palavras de contexto geral (+18)
TERMOS_18_LOCAIS = [
    # Palavras de Contexto Geral Violento ou Adulto (+18)
    "morte", "morto", "matou", "assassinato", "assassino", "sangue", "sangrento", 
    "violência", "gore", "tortura", "suicídio", "decapitação", 
    "sexo", "sexual", "erótico", "nudez", "pelado", "pelada", "pornô", "porno", "nudes",  
    "hentai", "explícito", "🔞", "adulto", "kamasutra", "onlyfans", "putaria", "puta",
    
    # Franquia GTA e derivados
    "Grand Theft Auto", "GTA", "GTA 5", "GTA5", "GTA V", "GTA RP", "GTA SA", 
    "GTA San Andreas", "FiveM", "MTA", "Roleplay",
    
    # Tiro / FPS / Guerra +18
    "Call of Duty", "CoD", "Warzone", "Black Ops", "MW2", "MW3", 
    "Counter Strike", "CSGO", "CS:GO", "CS2", "Rainbow Six", "R6", "Doom", 
    "Gears of War", "Left 4 Dead", "L4D", "L4D2", "Battlefield", "BF4", "BF1", "BFV", "Pubg", "PlayerUnknown", "Free Fire", "FF",
    
    # Terror / Sobrevivência
    "Resident Evil", "RE2", "RE3", "RE4", "RE7", "RE8", "RE Village", "RE4R", "Resident",
    "Dead Space", "Outlast", "Silent Hill", "Phasmophobia", "Lethal Company", 
    "Dead by Daylight", "DBD", "FNAF", "Five Nights", "Amnesia", "Slender", "Outlast 2",
    "Cry of Fear", "Dead Island", "Friday the 13th", "Sexta-Feira 13", "Until Dawn", 
    "The Evil Within", "SOMA", "DEVOUR", "Dying Light", "Rust",
    
    # RPG / Ação (Souls-like, Aventura violenta)
    "Cyberpunk 2077", "Cyberpunk", "The Witcher", "Witcher", "TW3", 
    "Elden Ring", "Bloodborne", "Dark Souls", "Sekiro", "Nioh",
    "Red Dead Redemption", "Red Dead", "RDR2", "RDR", 
    "The Last of Us", "TLOU", "TLOU 2", "TLOU2", "God of War", "GoW", "Dias Idos", "Days Gone", "Assassin's Creed", "Detroit Become Human",
    
    # Luta Violenta / Sangue
    "Mortal Kombat", "MK", "MK1", "MK11", "MKX", "Mortal", "Fatality"
]

def check_game_18_plus(game_name):
    with dict_lock:
        if game_name in game_rating_cache:
            return game_rating_cache[game_name]
    
    for j in TERMOS_18_LOCAIS:
        if re.search(r'\b' + re.escape(j.lower()) + r'\b', game_name.lower()):
            with dict_lock:
                game_rating_cache[game_name] = True
            return True
            
    with dict_lock:
        game_rating_cache[game_name] = False
    return False
def get_session():
    if not hasattr(thread_local, "session"):
        thread_local.session = requests.Session()
    return thread_local.session

def extrair_nome_canal_url(url):
    parsed = urllib.parse.urlparse(url)
    path_parts = parsed.path.strip('/').split('/')
    if path_parts:
        return path_parts[-1].replace('@', '')
    return "canal"

def extrair_nome_canal_real(url):
    try:
        html = requests.get(url, timeout=5).text
        match = re.search(r'<title>(.*?)</title>', html)
        if match:
            return match.group(1).replace(" - YouTube", "").strip()
    except Exception:
        pass
    return extrair_nome_canal_url(url)

async def get_video_details(session, video_id):
    url = f"https://www.youtube.com/watch?v={video_id}"
    title = None
    categoria = "Desconhecida"
    is_18_plus = False
    nome_jogo = None
    try:
        async with session.get(url, timeout=10) as response:
            html = await response.text()
        
        # Obter Título como plano B
        match_title = re.search(r'<title>(.*?)</title>', html)
        if match_title:
            title = match_title.group(1).replace(" - YouTube", "").strip()
            
        # Obter Categoria
        match_cat = re.search(r'"category":"([^"]+)"', html)
        if match_cat:
            categoria = match_cat.group(1)
            # Se for Gaming, tenta descobrir qual é o jogo
            if categoria == "Gaming":
                # Procura a caixa oficial de metadados de jogo do YouTube
                match_game = re.search(r'"style":"RICH_METADATA_RENDERER_STYLE_BOX_ART".{0,500}?"title":\{"simpleText":"([^"]+)"\}', html)
                if match_game:
                    jogo = match_game.group(1)
                    nome_jogo = jogo
                    is_18_plus = check_game_18_plus(jogo)
                    alerta = " [ALERTA: JOGO +18]" if is_18_plus else ""
                    categoria = f"Gaming (Jogo: {jogo}){alerta}"
                else:
                    categoria = "Gaming (Jogo não especificado oficialmente)"
    except Exception:
        pass
    return title, categoria, is_18_plus, nome_jogo

async def process_video(session, delay_sem, video, progresso, total_videos):
    async with delay_sem:
        videoId = video.get('videoId')
        title_runs = video.get('title', {}).get('runs', [])
        title = title_runs[0].get('text') if title_runs else None
        
        html_title, categoria, is_18_plus, nome_jogo = await get_video_details(session, videoId)
        
        # Se o título não veio no dicionário original do scrapetube, usa o da página HTML
        if not title:
            title = html_title if html_title else "Título não encontrado"

        # Verificação Secundária: Buscar termos +18 (jogos ou contexto geral) no TÍTULO do vídeo
        if not is_18_plus and title:
            for termo in TERMOS_18_LOCAIS:
                if re.search(r'\b' + re.escape(termo.lower()) + r'\b', title.lower()):
                    is_18_plus = True
                    nome_jogo = termo
                    categoria += f" [ALERTA: CONTEÚDO +18 IDENTIFICADO NO TÍTULO]"
                    break
        
        # Imprimir resultado assim que terminar a requisição individual
        progresso['count'] += 1
        pct = (progresso['count'] / total_videos) * 100
        marca_18 = f" {R}{B}[!! +18 !!]{W}" if is_18_plus else ""
        
        # Linha de progresso mais limpa
        print(f"{C}[{progresso['count']}/{total_videos}] ({pct:4.1f}%){W} {G}OK:{W} {title[:60]}{marca_18}")
                    
        return videoId, title, categoria, is_18_plus, nome_jogo

async def async_main(args):
    # Cabeçalho do programa
    print("YOUTUBE EXTRATOR > VIGIAR E PUNIR!\n")
    
    channel_url_raw = args.url.strip()
    if not channel_url_raw:
        print("URL inválida.")
        return

    # Garante que a URL base seja usada
    channel_url = re.sub(r'/(videos|shorts|streams|featured|playlists|community|channels|about)/?$', '', channel_url_raw)

    print(f"\nAguarde, buscando informações do canal: {channel_url}\n")
    
    try:
        # Pega as informações básicas
        nome_real = extrair_nome_canal_real(channel_url)
        
        v_gen = scrapetube.get_channel(channel_url=channel_url, content_type='videos', sleep=0, limit=args.limit)
        s_gen = scrapetube.get_channel(channel_url=channel_url, content_type='shorts', sleep=0, limit=args.limit)
        st_gen = scrapetube.get_channel(channel_url=channel_url, content_type='streams', sleep=0, limit=args.limit)
        videos_generator = itertools.chain(v_gen, s_gen, st_gen)
        
        print(f"Canal encontrado: {nome_real}")
        print(f"Coletando a lista de vídeos... (Limitado a {args.limit} por tipo se definido)")
        
        videos_list = []
        video_ids = set()
        for v in videos_generator:
            v_id = v.get('videoId')
            if v_id and v_id not in video_ids:
                video_ids.add(v_id)
                videos_list.append(v)
                print(f"-> Buscando da página... {len(videos_list)} encontrados", end="\r")
        print() 
        
        total_videos = len(videos_list)
        
        if total_videos == 0:
            print("Nenhum vídeo encontrado para este canal.")
            return

        print(f"\nProcessando {total_videos} vídeos...\n")
        
        progresso = {'count': 0}
        semaphore = asyncio.Semaphore(200)
        
        async with aiohttp.ClientSession() as session:
            tasks = []
            for video in videos_list:
                tasks.append(process_video(session, semaphore, video, progresso, total_videos))
            
            resultados = await asyncio.gather(*tasks)
        
        # Agrupamento e estatísticas
        jogos_18_count = 0
        videos_18_agrupados = {}
        dados_finais = []

        for res in resultados:
            videoId, title, categoria, is_18_plus, nome_jogo = res
            video_data = {
                "id": videoId,
                "title": title,
                "url": f"https://www.youtube.com/watch?v={videoId}",
                "category": categoria,
                "is_18_plus": is_18_plus,
                "game_term": nome_jogo
            }
            dados_finais.append(video_data)
            
            if is_18_plus:
                jogos_18_count += 1
                grupo = (nome_jogo if nome_jogo else "Termo não identificado").upper()
                if grupo not in videos_18_agrupados:
                    videos_18_agrupados[grupo] = []
                videos_18_agrupados[grupo].append(video_data)

        # Salvar Arquivos
        canal_id = extrair_nome_canal_url(channel_url)
        porcentagem_18 = (jogos_18_count / total_videos * 100) if total_videos > 0 else 0
        
        if args.format == 'txt':
            save_txt(canal_id, nome_real, channel_url, total_videos, dados_finais, videos_18_agrupados, jogos_18_count)
        elif args.format == 'csv':
            save_csv(canal_id, dados_finais, is_18_only=False)
            if jogos_18_count > 0:
                videos_18_list = [v for v in dados_finais if v['is_18_plus']]
                save_csv(f"+18_{canal_id}", videos_18_list, is_18_only=True)
        elif args.format == 'json':
            full_data = {
                "channel_metadata": {"name": nome_real, "url": channel_url, "total": total_videos},
                "stats": {"restricted_count": jogos_18_count, "restricted_percentage": f"{porcentagem_18:.1f}%"},
                "videos": dados_finais
            }
            save_json(canal_id, full_data)
            if jogos_18_count > 0:
                restricted_data = full_data.copy()
                restricted_data["videos"] = [v for v in dados_finais if v['is_18_plus']]
                save_json(f"+18_{canal_id}", restricted_data)

        # Relatório Final no Console (Premium Design)
        print(f"\n{G}{B}» CONCLUÍDO!{W} Dados exportados em {args.format.upper()}.")
        print(f"\n{C}╔{'═'*50}╗{W}")
        print(f"{C}║{W}          {B}RELATÓRIO DE CONTEÚDO DO CANAL{W}          {C}║{W}")
        print(f"{C}╠{'═'*50}╣{W}")
        print(f"{C}║{W} Total de vídeos processados.....: {total_videos:14} {C}║{W}")
        print(f"{C}║{W} Conteúdo +18 identificado.......: {R}{jogos_18_count:14}{W} {C}║{W}")
        print(f"{C}║{W} Porcentagem de restrição........: {Y}{porcentagem_18:13.1f}%{W} {C}║{W}")
        print(f"{C}╚{'═'*50}╝{W}")
        
        if porcentagem_18 >= 30:
            print(f"\n{R}{B} VEREDITO: ESTE CANAL POSSUI FOCO EM CONTEÚDO +18! {W}")
        elif porcentagem_18 > 0:
            print(f"\n{Y}{B} VEREDITO: O canal tem alguns jogos +18 (Mix de conteúdo). {W}")
        else:
            print(f"\n{G}{B} VEREDITO: Nenhum jogo +18 detectado na amostragem. {W}")
        print("-" * 52 + "\n")
        
    except Exception as e:
        print(f"Ocorreu um erro: {e}")

def save_txt(canal_id, nome_real, channel_url, total_videos, videos, videos_18_agrupados, jogos_18_count):
    nome_arquivo = f"videos_{canal_id}.txt"
    nome_arquivo_18 = f"videos_+18_{canal_id}.txt"

    with open(nome_arquivo, "w", encoding="utf-8") as f:
        f.write("YOUTUBE EXTRATOR > VIGIAR E PUNIR!\n\n")
        f.write(f"nome: {nome_real}\n")
        f.write(f"url: {channel_url}\n")
        f.write(f"quantidade de vídeos: {total_videos}\n\n")
        f.write("-" * 60 + "\n\n")
        for v in videos:
            f.write(f"*NOME> {v['title']}\n")
            f.write(f"*URL> {v['url']}\n")
            f.write(f"*CATEGORIA> {v['category']}\n")
            f.write("-" * 60 + "\n")

    if jogos_18_count > 0:
        with open(nome_arquivo_18, "w", encoding="utf-8") as f18:
            f18.write("YOUTUBE EXTRATOR > VIGIAR E PUNIR! (SOMENTE +18)\n\n")
            f18.write(f"nome: {nome_real}\n")
            f18.write(f"url: {channel_url}\n")
            f18.write(f"total vídeos +18 apontados: {jogos_18_count}\n\n")
            f18.write("=" * 60 + "\n")
            f18.write("                SUMÁRIO DE OCORRÊNCIAS\n")
            f18.write("=" * 60 + "\n")
            
            grupos_ordenados = sorted(videos_18_agrupados.items(), key=lambda x: len(x[1]), reverse=True)
            for grupo, lista in grupos_ordenados:
                f18.write(f"-> {grupo}: {len(lista)} vídeo(s)\n")
            
            f18.write("\n" + "=" * 60 + "\n")
            f18.write("                OCORRÊNCIAS DETALHADAS\n")
            f18.write("=" * 60 + "\n\n")
            
            for grupo, lista in grupos_ordenados:
                f18.write(f"=== {grupo} ===\n")
                for v in lista:
                    f18.write(f"*TÍTULO> {v['title']}\n")
                    f18.write(f"*URL> {v['url']}\n")
                    f18.write("-" * 40 + "\n")
                f18.write("\n")

def save_csv(canal_id, videos, is_18_only=False):
    suffix = "" if not is_18_only else "" # o id ja vem com +18 se for o caso
    nome_arquivo = f"videos_{canal_id}.csv"
    with open(nome_arquivo, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["id", "title", "url", "category", "is_18_plus", "game_term"])
        writer.writeheader()
        writer.writerows(videos)

def save_json(canal_id, data):
    nome_arquivo = f"videos_{canal_id}.json"
    with open(nome_arquivo, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='YouTube Extrator - Vigiar e Punir!')
    parser.add_argument('url', help='URL do canal do YouTube')
    parser.add_argument('--format', choices=['txt', 'csv', 'json'], default='txt', help='Formato de saída (padrão: txt)')
    parser.add_argument('--limit', type=int, default=None, help='Limite de vídeos por tipo (videos, shorts, lives)')
    
    args = parser.parse_args()

    import sys
    # Conserto do event loop policy para Windows
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(async_main(args))
