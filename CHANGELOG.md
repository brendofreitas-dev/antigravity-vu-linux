# Changelog

Todas as alterações notáveis neste projeto serão documentadas neste arquivo.

O formato baseia-se em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
e este projeto adere ao [Semantic Versioning](https://semver.org/lang/pt-BR/).

---

## [1.1.0] - 2026-11-12

### Adicionado
- **Unified Dynamic Island (Date/Time + Antigravity)**: cápsula única no centro da Top Bar englobando o `DateMenu` nativo; clique na data/hora abre o calendário do GNOME, clique no lado Antigravity abre o Dashboard.
- **Adaptive Ubuntu System Theme (Light/Dark)**: segue `color-scheme`, `gtk-theme` e `accent-color` (9 cores Yaru/Adwaita).
- `AGENTS.md` com topologia de agentes e regras de engenharia.

### Corrigido
- **PopupMenu** achatado/vazio no GNOME Shell 50: substituído `St.ScrollView` por `PopupMenuSection` e layouts com `orientation`.

---

## [1.0.0] - 2026-11-12

### Adicionado
- **Extensão GNOME Shell (45 a 50+)**:
  - Implementação completa em arquitetura ECMAScript Modules (ESM) para GNOME 45, 46, 47, 48, 49 e 50.
  - Integração no `Main.panel._centerBox` adjacente ao `dateMenu` nativo, mantendo data, hora e notificações intocadas.
  - Dynamic Island com 3 estágios visuais:
    - Pílula compacta de repouso (28px) com dot indicador de saúde da cota e porcentagem.
    - Expansão dinâmica em hover ou transição de atividade com métricas imediatas de contexto e contagem de agentes.
    - Painel suspenso *Dark Glassmorphism* com barras de progresso de cotas, contadores regressivos de reset, estatísticas de prompt cache e ranking de projetos.
  - Atualização assíncrona não-bloqueante via `Gio.Subprocess` sem impacto na fluidez do desktop (0.0% CPU idle).
- **Backend de Telemetria (`ag-vu`)**:
  - Coletor autônomo em Python 3 puro sem dependências externas.
  - Descoberta automática de instâncias ativas do Antigravity Language Server via `hub_*.json` e variáveis de ambiente.
  - Consulta ao RPC local `RetrieveUserQuotaSummary` para leitura de cotas do Gemini 4 Argon, Gemini Pro/Flash e modelos terceiros (Claude/GPT).
  - Consulta a banco SQLite `conversation_summaries.db` em modo leitura estrita (`mode=ro`) para detecção em tempo real de swarm e sessões ativas.
  - Indexador incremental de transcripts com verificação de `mtime_ns` e tamanho de arquivo em `~/.cache/antigravity-vu/transcript_index.json`.
  - Cache persistente de cotas para exibição offline quando a IDE estiver fechada.
  - Interface CLI com suporte a `--json`, `--pretty` (dashboard colorido no terminal), `--watch` e `--pin-group`.
- **Scripts de Instalação e Gerenciamento**:
  - Script `install.sh` para instalação automatizada do binário CLI em `~/.local/bin` e registro da extensão no GNOME Shell.
  - Script `uninstall.sh` para remoção limpa de todos os artefatos.
- **Suíte de Testes e Documentação**:
  - Testes unitários e de integração em `tests/test_collector.py`.
  - Documentação completa de arquitetura em `docs/ARCHITECTURE.md`.
  - Guia de contribuição em `CONTRIBUTING.md` e roadmap estratégico em `ROADMAP.md`.
