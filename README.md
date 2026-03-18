# YouTube Extrator - Vigiar e Punir! 🔞

Ferramenta profissional para auditoria de canais do YouTube, focada em identificar conteúdo restrito (+18) através de cruzamento de metadados de jogos e termos sensíveis.

## 🚀 Funcionalidades
- **Mineração Assíncrona**: Processamento simultâneo de até 200 vídeos por vez (via `asyncio` e `aiohttp`).
- **Detecção Inteligente**: Identifica jogos maduros (GTA, Resident Evil, Mortal Kombat) e gírias da comunidade.
- **Múltiplos Formatos**: Exportação para **TXT**, **CSV** e **JSON**.
- **CLI Robust**: Uso via linha de comando com parâmetros de limite e formato.

## 📦 Instalação

1. Clone o repositório ou baixe os arquivos.
2. Com o Python instalado, execute:
   ```bash
   pip install -e .
   ```
   *Ou instale manualmente:*
   ```bash
   pip install requests aiohttp scrapetube
   ```

## 🛠️ Como Usar

O script agora funciona via linha de comando (CLI).

### Uso Básico (TXT)
```bash
python main.py https://www.youtube.com/@alanzoka
```

### Exportar para CSV
```bash
python main.py https://www.youtube.com/@alanzoka --format csv
```

### Exportar para JSON
```bash
python main.py https://www.youtube.com/@alanzoka --format json
```

### Limitar Amostragem (Últimos 10 vídeos por tipo)
```bash
python main.py https://www.youtube.com/@alanzoka --limit 10
```

## 📄 Estrutura de Arquivos
- **videos_[canal].[ext]**: Lista completa de vídeos com categoria.
- **videos_+18_[canal].[ext]**: Relatório detalhado apenas das infrações encontradas. Disponível em **TXT**, **CSV** e **JSON**.


---
*Desenvolvido em parceria com Antigravity.*
