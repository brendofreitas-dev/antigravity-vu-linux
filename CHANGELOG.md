# Changelog

Todas as alterações notáveis neste projeto serão documentadas neste arquivo.

O formato baseia-se em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
e este projeto adere ao [Semantic Versioning](https://semver.org/lang/pt-BR/).

---

## [1.2.3] - 2026-11-12

### Adicionado
- **Detecção do modelo ativo real (`detect_active_model`)**:
  - Extração do modelo em uso e nível (`Gemini 4 Hydrogen (XHigh)`, `Gemini 3.8 Flash (High)`, `Gemini 4 Argon (Low)`, `Claude Opus 5.5 (Low)`) a partir da tabela `gen_metadata` do SQLite da sessão ativa.
  - Campos `active_model`, `active_model_label` e `active_model_group` incluídos em `active_context`.
  - Exibição de badge destacado (`🤖 {active_model_label}`) no card de Sessão Ativa & Swarm.
- **Inteligência do modo Auto (`pinned_group == "auto"`)**:
  - A cota primária na Top Bar agora acompanha dinamicamente o grupo do modelo ativo na IDE (ex: `4 Hydrogen 48%` ou `Gemini 3.8 48%` ao trabalhar com Hydrogen/Flash), com fallback para o menor bucket apenas se nenhum modelo ativo for detectado.
- **Versão dinâmica no rodapé**:
  - O rodapé da extensão consome dinamicamente o campo `"version-name"` do `metadata.json`, eliminando números de versão hardcoded.

### Alterado
- **Visual nativo translúcido idêntico ao Calendar do Ubuntu**:
  - Contêiner `.ag-popup-menu` 100% transparente, herdando o fundo translúcido, blur, bordas e sombras nativos de `.popup-menu-content` do GNOME Shell / Yaru Calendar.
  - Sub-cards adaptados com transparência suave (`rgba(255, 255, 255, 0.06)` no Dark / `rgba(0, 0, 0, 0.045)` no Light).
- **Cabeçalho distribuído de 420px**:
  - Título à esquerda com expansão flexível e badges (`[Pro]`, `● Online`, `[↻]`) distribuídos e alinhados à direita, aproveitando toda a largura do menu.
- **Suíte de testes expandida**:
  - Novos testes `test_auto_active_model_selection` e `test_detect_active_model_from_db`, alcançando 13/13 testes aprovados.

---

## [1.2.2] - 2026-11-12

### Alterado
- **Estilo nativo da Top Bar (padrão Ubuntu System Tray)**:
  - Em repouso (sem hover): cápsula `.ag-unified-island-capsule` 100% transparente, sem borda estática, sem fundo cinza fixo e sem sombras externas, integrando-se de forma limpa ao painel superior do GNOME.
  - No hover: adota o realce nativo dos botões da Top Bar do tema Ubuntu Yaru (`box-shadow: inset 0 0 0 100px rgba(255, 255, 255, 0.17)`, `border: 3px solid transparent`, `border-radius: 999px`), iluminando a cápsula de forma contínua e monolítica sem divisões internas.
  - No clique (`:active`): realce nativo reforçado com `rgba(255, 255, 255, 0.28)`.
  - Cores dos textos da Top Bar mantidas em tons claros (`#f8fafc` / `#cbd5e1`) mesmo com o sistema em Light Mode, acompanhando a barra superior escura nativa do Ubuntu Yaru.

---

## [1.2.1] - 2026-11-12

### Alterado
- **Identificação clara de modelos e separação de quotas**:
  - Grupo `gemini` formalizado como **Gemini 3.8 Flash & 4 Hydrogen** nos cartões e **Gemini 3.8** na Top Bar, refletindo o pool compartilhado de capacidade (janelas 5h e semanal).
  - Grupo `3p` formalizado como **Claude & GPT (Opus / Sonnet / GPT)** nos cartões e **Claude / GPT** na Top Bar.
  - Grupo `argon` formalizado como **Gemini 4 Argon**.
- **Cálculo de gargalo ativo (bucket mais restritivo)**:
  - Ao fixar um grupo com múltiplos limites (ex: 5h e semanal), o coletor backend (`ag_vu_collector.py`) e a extensão (`island.js`) selecionam ativamente o bucket de menor percentual restante (`remaining_pct`), alertando o gargalo operacional real (ex: se 5h bater 0%, exibe 0% mesmo com cota semanal disponível).
- **Legendas de modelos nos cartões do dashboard**:
  - Subtítulo compacto (`.ag-group-desc`) abaixo do cabeçalho de cada cartão exibindo os modelos que compartilham a cota (ex: `Gemini 3.8 Flash, Gemini 4 Hydrogen, Gemini 3.5 Lite` e `Claude Opus 5.5, Claude Sonnet 5.5, GPT-OSS 120B`).
- **Metadados ricos no coletor backend (`ag_vu_collector.py`)**:
  - Adicionados campos `description` e `models` por grupo de quotas; campo `group_name` adicionado em `primary_quota`, com `pill_name` mantendo Non-Breaking Space para retrocompatibilidade na Top Bar.
- **Suíte de testes expandida**:
  - Adicionado teste `test_pinned_group_most_restrictive_bucket`, totalizando 11/11 testes unitários aprovados.

---

## [1.2.0] - 2026-11-12

### Alterado
- **Dynamic Island monolítica** (inspirada no Volum): a cápsula é uma superfície única e contínua, sem divisor vertical nem caixas internas.
- Neutralizadas as sub-pílulas do tema Yaru (`#panel .panel-button` com `box-shadow: inset` no hover) dentro da cápsula, via seletores de alta especificidade em `#panel .ag-unified-island-capsule .panel-button` (`:hover`, `:focus`, `:active`, `:checked`, `:overview`) e `.clock-display`/`.clock`.
- O hover pertence à ilha inteira (`.ag-unified-island-capsule:hover`: borda e sombra mais claras); removidos os hovers separados de data e indicador.
- Espaçamento interno ajustado (data `0 10px 0 14px`, indicador `0 14px 0 6px`).

---

## [1.1.3] - 2026-11-12

### Corrigido
- **Hot-reload real**: o `import()` dinâmico agora usa `file://${path}/island.js?t=<timestamp>`; sem o esquema `file://` o GJS falhava e caía no import estático (cacheado na sessão).
- **Nomes de grupos no backend** (`ag_vu_collector.py`): `Gemini Models` → `Gemini\u00a03.8`, `Claude and GPT models` → `Claude / GPT`, `Gemini 4 Argon` mantido. O NBSP evita que versões antigas da extensão em memória removam o prefixo `Gemini ` e exibam `Models`.
- `island.js` normaliza `\u00a0` para espaço simples ao formatar nomes de grupos.

---

## [1.1.2] - 2026-11-12

### Corrigido
- **Top Bar**: texto cortado/deslocado na cápsula; a pílula interna aninhada perdeu fundo, borda e margens, e o indicador usa `y_align: CENTER` / `y_expand: true`.
- **Nome da cota**: `Gemini Models` aparecia como `Models` (replace sensível a maiúsculas). Novos `formatShortGroupName`/`formatDisplayGroupName`: `Gemini 3.8`, `4 Argon`, `Claude/GPT`.
- **PopupMenu**: layout compacto; com mais de 4 agentes a lista rola em `St.ScrollView` (`max-height: 135px`), mantendo o menu dentro da tela.

---

## [1.1.1] - 2026-11-12

### Alterado
- **Hot-reload**: `extension.js` virou um carregador que faz `import('island.js?t=<timestamp>')` com cache-busting; `gnome-extensions disable && enable` aplica mudanças de lógica/UI sem reiniciar a sessão (fallback para import estático).
- **Paleta fiel ao Ubuntu Yaru**: Dark (menu `#36363a`, cards `#2a2a2e`, cápsula `rgba(45,45,50,0.90)`) e Light (menu `#ffffff`, cards `#f4f4f6`), eliminando o tom azulado.
- **Detecção de tema**: `prefer-light` = sempre Light, `prefer-dark` = sempre Dark; `gtk-theme` só é consultado com `color-scheme` `default`. Também escuta `St.ThemeContext` `changed`.

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
