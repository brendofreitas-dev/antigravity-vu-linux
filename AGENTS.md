# AGENTS.md — Antigravity View Usage

- **Projeto**: `/home/brendo.freitas/Projetos/antigravity-vU-linux` (remoto `brendofreitas-dev/antigravity-vu-linux`)
- **Resumo**: extensão GNOME Shell 45–50+ (Unified Dynamic Island: Data/Hora + Antigravity; tema adaptativo Ubuntu Light/Dark) + backend Python `ag-vu`.

## Topologia de agentes
| Agente | Responsabilidade | Modelo |
| :--- | :--- | :--- |
| `coordinator` | Planejamento e interação com o usuário | Orchestrator (Carbon) (`gemini-pro-orchestrator`) |
| `gnome-dev` | `extension/island.js`, `extension/extension.js`, `extension/stylesheet.css`, `extension/metadata.json`, `extension/schemas/*`, `install.sh` | Gemini 4 Hydrogen (High) (`gemini-4-hydrogen-high`) |
| `explorer` | `backend/ag_vu_collector.py`, `tests/test_collector.py` | Gemini 4 Hydrogen (High) (`gemini-4-hydrogen-high`) |
| `verifier` | Testes, auditoria de código e documentação, validação em runtime | Gemini 4 Hydrogen (High) (`gemini-4-hydrogen-high`) |
| `researcher` | Pesquisa técnica e referências UI/UX | Gemini 4 Hydrogen (Medium) (`gemini-4-hydrogen-medium`) |
| `docs-agent` | `README.md`, `CHANGELOG.md`, `ROADMAP.md`, `CONTRIBUTING.md`, `docs/`, `AGENTS.md` | Gemini 4 Hydrogen (Medium) (`gemini-4-hydrogen-medium`) |
| `git-release` | Commits semânticos, tags, push e Releases | Gemini 3.8 Flash (High) (`gemini-3.8-flash-high`) |
| `monitor` | Monitoramento do quadro do Swarm | Gemini 3.8 Flash (High) (`gemini-3.8-flash-high`) |

## Arquitetura
- `backend/ag_vu_collector.py`: coletor Python puro (RPC local, SQLite `mode=ro`, índice de transcripts); CLI `ag-vu`.
- `extension/`: ESM; `_centerBox` vira `.ag-unified-island-capsule`, `dateMenu` nativo preservado, `disable()` restaura tudo.
- Tema: `org.gnome.desktop.interface` → `.ag-theme-dark` / `.ag-theme-light` + accent.
- Detalhes: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Regras de engenharia contínua
1. Cada agente edita apenas seus próprios arquivos.
2. Zero overhead: sem loops de redesenho; coleta assíncrona via `Gio.Subprocess`.
3. Tudo criado em `enable()` deve ser desfeito em `disable()`.
4. Suíte `python3 -m unittest discover -s tests` deve passar antes de release.
5. Conventional Commits; nunca expor tokens em arquivos ou `.git/config`.
6. Documentação atualizada a cada release (CHANGELOG, ROADMAP, ARCHITECTURE).
