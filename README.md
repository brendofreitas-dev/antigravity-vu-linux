# ⚡ Antigravity View Usage (Dynamic Island GNOME)

[![GNOME Shell](https://img.shields.io/badge/GNOME%20Shell-45%20%7C%2046%20%7C%2047%20%7C%2048%20%7C%2049%20%7C%2050-blue?logo=gnome&logoColor=white)](https://extensions.gnome.org)
[![Python](https://img.shields.io/badge/Python-3.10%2B-green?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Architecture](https://img.shields.io/badge/Architecture-ESM%20GJS%20%2B%20Zero--Dep%20CLI-purple)]()

> **Dynamic Island elegante e de altíssima performance para a Top Bar do GNOME Shell.**
> Monitore cotas de IA (Gemini 4 Argon, Gemini Models, Claude/GPT 3P), janela de contexto ativa, agentes paralelos (*swarm*) e consumo mensal de tokens em tempo real com **zero overhead** de CPU e RAM.

---

```
                       TOP BAR DO GNOME SHELL (CENTRO)
 ┌──────────────────────────────────┐   ┌───────────────────────────────┐
 │     Qua 12 Nov  10:58 BRT        │   │  ● Argon 31.4% │ Ctx: 48.2k   │
 └──────────────────────────────────┘   └───────────────────────────────┘
          (Data & Hora Nativa)              (Dynamic Island Antigravity)
```

---

## ✨ Destaques & Funcionalidades

- 🏝️ **Dynamic Island Centralizada**: Integrada cirurgicamente ao lado do `DateMenu` nativo do GNOME Shell. Preserva data, hora e calendário intocados enquanto o Mutter auto-centraliza o conjunto com fluidez.
- ⚡ **Monitor de Cotas em Tempo Real**: Telemetria direta via ConnectRPC do daemon local do Antigravity (`RetrieveUserQuotaSummary`), cobrindo Gemini 4 Argon, Gemini Pro/Flash e modelos Claude/GPT com percentuais e contagem regressiva de reset (`reset_in`).
- 🧠 **Rastreador de Swarm & Agentes Ativos**: Visualização em tempo real de sessões e subagentes trabalhando em paralelo (`coordinator`, `explorer`, `gnome-dev`, `verifier`, etc.), status operacional (`WORKING` / `IDLE`) e contagem de steps executados.
- 🎯 **Janela de Contexto & Prompt Cache**: Detecção do projeto ativo, medição exata de tokens de entrada (`input_tokens`), economia via prompt cache (`cache_read_tokens`) e tokens gerados (`output_tokens`).
- 📊 **Consumo Mensal & Ranking por Projeto**: Agregação incremental com índice em cache (`mtime_ns`), exibindo o total acumulado do mês e os projetos com maior tráfego.
- 🏎️ **Performance Absoluta (Zero-Overhead)**:
  - **0.0% de CPU** quando ocioso: sem loops de redesenho no compositor.
  - Animações aceleradas por hardware via Clutter (`actor.ease`).
  - Execução 100% assíncrona em background via `Gio.Subprocess` (sem engasgos na interface do GNOME).
- 🛠️ **CLI Independente (`ag-vu`)**: Utilitário de linha de comando incluído com saída JSON estruturada, visualização formatada em tabela para terminal e modo de monitoramento contínuo (`--watch`).

---

## 📸 Os 3 Estágios da Dynamic Island

| Estágio | Comportamento | Visual |
| :--- | :--- | :--- |
| **1. Pílula Fechada** | Discreta (28px de altura), dot com cor de status (verde/âmbar/vermelho) e porcentagem da quota principal. | `[ ● Argon 31.4% ]` |
| **2. Expansão Dinâmica** | Ao passar o cursor ou quando agentes iniciam trabalho, expande suavemente exibindo contexto e agentes ativos. | `[ ● Argon 31.4% │ Ctx: 48.2k • ⚡ 3 ag ]` |
| **3. Dashboard Completo** | Ao clicar, abre o menu suspenso em estilo Dark Glassmorphism com barras de progresso, breakdown de tokens e lista de agentes. | *(Popup expansivo de alta densidade informativa)* |

---

## 🚀 Instalação Rápida

### Pré-requisitos
- **Sistema Operacional**: Linux com **GNOME Shell 45, 46, 47, 48, 49 ou 50** (Ubuntu 24.04+, Fedora 39+, Arch Linux, etc.).
- **Python**: Versão 3.10 ou superior (sem necessidade de bibliotecas externas via pip).
- **Google Antigravity IDE**: Instalado e em execução.

### Instalação em 1 Comando

Clone o repositório e execute o script de instalação:

```bash
git clone https://github.com/brendo-freitas/antigravity-vU-linux.git
cd antigravity-vU-linux
./install.sh
```

O script automaticamente:
1. Instala o binário CLI em `~/.local/bin/ag-vu`.
2. Instala a extensão GNOME Shell em `~/.local/share/gnome-shell/extensions/antigravity-vu@brendo.freitas`.
3. Habilita a extensão imediatamente no GNOME Shell.

> **Dica**: No Wayland, se a extensão não aparecer imediatamente, faça logout e login novamente ou use o utilitário `gnome-extensions enable antigravity-vu@brendo.freitas`. No X11, basta pressionar `Alt + F2`, digitar `r` e teclar Enter.

---

## 💻 Uso do CLI (`ag-vu`)

O coletor pode ser utilizado diretamente no seu terminal:

```bash
# Visualizar dashboard interativo e colorido no terminal
ag-vu --pretty

# Modo de monitoramento contínuo (atualização a cada 2 segundos)
ag-vu --watch

# Obter saída em JSON bruto para scripts ou automações
ag-vu --json

# Fixar um grupo de quotas específico na pílula fechada (auto, argon, gemini, 3p)
ag-vu --pin-group argon
```

### Exemplo de Saída (`ag-vu --pretty`):

```text
┌────────────────────────────────────────────────────────────────────────┐
│  ANTIGRAVITY VIEW USAGE                                 Plano: Pro (●) │
├────────────────────────────────────────────────────────────────────────┤
│  COTAS ATIVAS                                                          │
│  • Gemini 4 Argon     [████░░░░░░]  31.4%   Reset em: 3d 5h            │
│  • Gemini Models      [███████░░░]  64.3%   Reset em: 3d 5h            │
│  • Claude & GPT (3P)  [██████████] 100.0%   Reset em: 6d 23h           │
├────────────────────────────────────────────────────────────────────────┤
│  SESSÃO ATIVA & SWARM                                                  │
│  • Projeto: antigravity-vU-linux                                       │
│  • Contexto: 48.2k (In: 12.4k | Prompt Cache: 35.8k | Out: 4.1k)       │
│  • Agentes: 3 ativos (coordinator: 14 steps, explorer: 8 steps)        │
├────────────────────────────────────────────────────────────────────────┤
│  MÊS ATUAL (2026-11)                                                   │
│  • In: 1.25M  │  Cache: 8.42M  │  Out: 185k  │  Total: 9.86M           │
└────────────────────────────────────────────────────────────────────────┘
```

---

## ⚙️ Configuração Personalizada

As preferências ficam salvas em `~/.config/antigravity-vu/prefs.json`:

```json
{
  "pinned_group": "auto",
  "refresh_interval": 5,
  "expand_on_activity": true
}
```

- `pinned_group`: `"auto"` (exibe a cota com menor saldo restante), `"argon"`, `"gemini"` ou `"3p"`.
- `refresh_interval`: Intervalo de atualização da telemetria em segundos (padrão: 5).
- `expand_on_activity`: Se ativado, a Dynamic Island expande momentaneamente ao detectar que subagentes do swarm iniciaram trabalho.

---

## 🏛️ Arquitetura do Sistema

Para documentação aprofundada dos componentes internos, descoberta de sockets, formatos de cache e diagramas de sequência, consulte:
📖 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

---

## 🗑️ Desinstalação

Para remover a extensão e o binário do sistema:

```bash
cd antigravity-vU-linux
./uninstall.sh
```

---

## 🤝 Contribuições

Contribuições são muito bem-vindas! Consulte o guia de contribuição para configurar seu ambiente de desenvolvimento e executar testes:
📄 [CONTRIBUTING.md](CONTRIBUTING.md)

---

## 📜 Licença

Distribuído sob a licença **MIT**. Consulte [LICENSE](LICENSE) para mais detalhes.

Desenvolvido com dedicação para a comunidade de desenvolvedores de IA no Linux.
