# Changelog

Todas as alterações notáveis neste projeto serão documentadas neste arquivo.

O formato baseia-se em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
e este projeto adere ao [Semantic Versioning](https://semver.org/lang/pt-BR/).

---

## [1.5.2] - 2026-11-18

### Adicionado
- **Suporte às novas famílias de modelos do plano Google (`Orchestrator`, `Carbon`, `Claude 4.6`)**:
  - Regex protobuf em `detect_active_model` (`backend/ag_vu_collector.py`) atualizado para capturar modelos `Orchestrator` além de `Gemini`, `Claude` e `GPT-` (com classificação unificada `_classify_model_group` aplicada também ao fallback `antigravity_state.pbtxt`).
  - Parser dinâmico de descrições live do RPC (`"Models within this group:..."`) em `transform_quota_groups`, extraindo automaticamente `rpc_models` e compactando `"Orchestrator (Carbon), Orchestrator (Argon)"` para `"Orchestrator (Carbon/Argon)"`.
  - Resolução unificada de grupo no novo plano de 2 grupos: quando `active_model_group == "argon"` e o grupo `"argon"` dedicado não existir no payload, vincula automaticamente ao pool `"gemini"` (`Gemini 4 (Carbon / Argon / Hydrogen) & 3.8`).
  - Grupo `3p` atualizado para refletir **Claude Opus 4.6**, **Claude Sonnet 4.6** e **GPT-OSS 120B**.
- **Rótulos curtos na Top Bar e quebra de linha segura na UI (`extension/island.js`, `extension/stylesheet.css`)**:
  - Novos rótulos compactos na pílula: `Orch Carbon`, `Orch Argon`, `4 Carbon`, `4 Hydrogen`, `4 Argon`, `Gemini 3.8` e `Claude/GPT`.
  - Quebra de linha automática (`Pango.WrapMode.WORD_CHAR`, `ellipsize: NONE`, `max-width: 320px`) em `.ag-group-desc` para exibir descrições multi-modelo completas na coluna esquerda sem estouro horizontal.
- **Topologia do Swarm e Suíte de Testes**:
  - `AGENTS.md` e `docs/ARCHITECTURE.md` atualizados com a topologia completa dos 8 agentes e seus modelos do novo plano.
  - Suíte unitária expandida para **26/26 testes aprovados** (adicionados `test_detect_active_model_new_models_and_pbtxt_fallback` e `test_unified_plan_two_groups_new_models`).
  - `extension/metadata.json` atualizado para `version: 13` e `version-name: "1.5.2"`.

---

## [1.5.1] - 2026-11-13

### Corrigido
- **Sobrevivência do Indicador e Polling após Bloqueio de Tela / Reativação**:
  - Corrigido o bug onde o indicador desaparecia da Top Bar e o polling de 5s parava após ciclos de bloqueio e desbloqueio de tela (`disable()` seguido de `enable()`).
  - **Importação Determinística de Módulo**: Substituída a query string volátil `?t=${Date.now()}` por `?v=${sec}_${usec}_${size}` baseada nas propriedades de disco (`mtime` e tamanho de `island.js`). Durante ciclos de tela bloqueada sem alterações de arquivo, o GJS reutiliza o módulo em 0ms sem reavaliar scripts ou recriar tipos.
  - **Resolução Dinâmica de GType**: Implementada a função `resolveUniqueGTypeName` para evitar exceções de `Type name AntigravityUnifiedIndicator is already registered` durante hot-reloads na mesma sessão.
  - **Idempotência no Desmonte**: Guard `_destroyed` adicionado em `destroy()` para garantir desmonte seguro e idempotente, desconexão de `open-state-changed` do menu e proteção em callbacks assíncronos (`GLib.SOURCE_REMOVE`).
- **Metadados**:
  - `extension/metadata.json` atualizado para `version: 12` e `version-name: "1.5.1"`.

---

## [1.5.0] - 2026-11-13

### Adicionado
- **Indicador de Ritmo (*Pace Marker*) e Previsão de Esgotamento**:
  - Marcador vertical fino de 2px nas barras de cota indicando o consumo esperado para o tempo decorrido na janela (`weekly` ou `5h`).
  - Detecção de consumo acelerado (`pace_status: fast`) com badge âmbar e cálculo amigável do tempo estimado de esgotamento (`⚡ ~Xh`).
- **Mini Histograma de Atividade de 7 Dias**:
  - Gráfico compacto diário exibindo a distribuição de tokens nos últimos 7 dias na coluna direita do dashboard, com realce interativo no hover revelando data e consumo detalhado.
- **Notificações Nativas do Sistema (`Main.notify`) com Anti-Spam**:
  - Alertas automáticos do GNOME Shell para transições de cota crítica (<20% aviso, <10% crítico) e renovação de cota (reset para >=99.5%).
  - Inicialização silenciosa e controle de transições com persistência em `~/.cache/antigravity-vu/notify_state.json`.
- **Atalho de Teclado Global Configurável**:
  - Atalho padrão `<Super><Alt>a` para alternar a exibição do Dashboard, registrado via GSettings (`org.gnome.shell.extensions.antigravity-vu`).
- **Compatibilidade com Blur My Shell**:
  - Detecção dinâmica de `blur-my-shell@aunetx` com aplicação da classe `.ag-blur-compat` para bordas e translucidez integradas.
- **Suporte a Waybar (`--waybar`)**:
  - Nova flag CLI `ag-vu --waybar` que emite JSON em linha única compatível com status bars Wayland (`text`, `tooltip`, `class`, `percentage`).
- **Dashboard CLI (`ag-vu --pretty`)**:
  - Indicador de ritmo acelerado e sumário dos últimos 7 dias integrados ao visualizador de terminal.

### Alterado
- **Metadados e Instalação**:
  - `extension/metadata.json` atualizado para `version: 11`, `version-name: "1.5.0"` e `settings-schema`.
  - `install.sh` atualizado para instalação recursiva de schemas GSettings e compilação automática (`glib-compile-schemas`).
- **Suíte de Testes**:
  - Suíte unitária expandida para 24/24 testes cobrindo ritmo, esgotamento, histórico diário e saída Waybar.

---

## [1.4.1] - 2026-11-13

### Corrigido
- **Alinhamento e formato da legenda de cores (`.ag-color-legend`)**:
  - Reorganizada a grade interna em duas colunas verticais estritas (`colA` e `colB`) com expansão horizontal uniforme, alinhando com precisão os itens de ambas as colunas no eixo horizontal.
  - Dimensões dos pontos indicadores travadas em 8×8px (`x_expand: false`, `y_expand: false`, `y_align: CENTER` e restrições rígidas no CSS), eliminando a distorção vertical e garantindo formato circular perfeito.
- **Metadados**:
  - `extension/metadata.json` atualizado para `version: 10` e `version-name: "1.4.1"`.

---

## [1.4.0] - 2026-11-13

### Adicionado
- **Layout em 2 colunas equilibradas (720px estilo Ubuntu Calendar)**:
  - Painel expandido para 720px com distribuição harmoniosa em duas colunas.
  - **Coluna Esquerda (345px)**: Cotas de modelos com barras proporcionais (máximo 310px), Legenda de cores em grade 2×2 e Sessão Ativa com badge do modelo em uso e chips de tokens (`In / Cache / Out`).
  - **Coluna Direita (335px)**: Lista completa dos Agentes do Swarm com divisória sutil à esquerda, painel de Consumo Mensal com tokens agregados e ranking de Top Projetos.
- **Legenda de cores em grade 2×2 (`.ag-color-legend`)**:
  - Pontos reais `St.Widget` (7×7px) dispostos em grade 2×2 espaçada e limpa:
    - Linha 1: `● ≥50% Normal`  |  `● 20–49% Atenção`
    - Linha 2: `● <20% Crítico`  |  `● Agente Ativo`

### Alterado
- **Exibição direta dos Agentes do Swarm sem corte**:
  - Removido completamente o `St.ScrollView` da lista de agentes; todos os agentes do Swarm são exibidos diretamente na coluna direita, sem barras de rolagem cinzentas cortando o status ou a contagem de steps.
- **Metadados**:
  - `extension/metadata.json` atualizado para `version: 9` e `version-name: "1.4.0"`.

---

## [1.3.1] - 2026-11-12

### Corrigido
- **Rastreamento de hover e realce da cápsula unificada**:
  - Reativados `reactive = true` e `track_hover = true` em `_centerBox`, `_dateMenu` e no indicador do Antigravity.
  - Implementado sincronizador reativo `_syncCapsuleHover()` conectado via `notify::hover` e `open-state-changed` em ambos os menus, aplicando dinamicamente a classe `.ag-capsule-hovered`.
  - O realce em retângulo com cantos arredondados (8px) do Ubuntu System Tray (`box-shadow: inset 0 0 0 100px rgba(255, 255, 255, 0.17)`) agora acende com total confiabilidade ao passar o cursor sobre a Data/Hora, sobre as métricas ou enquanto os menus estiverem abertos.
  - Desconexão limpa e restauração completa de todos os manipuladores de sinais em `_removeUnifiedIsland()` e `destroy()`.
- **Metadados**:
  - `extension/metadata.json` atualizado para `version: 8` e `version-name: "1.3.1"`.

---

## [1.3.0] - 2026-11-12

### Removido
- **Botão manual de fixar modelo (`📌 Fixar`)**:
  - Removidos os botões `📌 Fixar` / `📌 Fixado` dos cartões do dashboard e o parâmetro `pinned_group` da extensão.
  - A Top Bar agora opera de forma **100% automática**, acompanhando dinamicamente o modelo ativo detectado pelo coletor (`ag-vu --json`).
- **Etapa 2 da Dynamic Island (Hover / Auto-peek de contexto e agentes na Top Bar)**:
  - Eliminado o morphing expansivo que exibia contexto e swarm na Top Bar ao passar o cursor ou ao iniciar agentes.
  - A barra superior agora permanece limpa, estável e livre de distrações (`Data/Hora  ● Modelo XX%`).

### Adicionado
- **Legenda visual de cores no Dashboard (`.ag-color-legend`)**:
  - Nova legenda compacta exibindo o significado de cada cor de status do indicador:
    - 🟢 `● ≥50% Normal` (Quota Saudável)
    - 🟠 `● 20-49% Atenção` (Quota Moderada)
    - 🔴 `● <20% Crítico` (Quota Baixa)
    - 🔵 `● Agente Ativo` (Agentes em execução no Swarm)

### Alterado
- **Retângulo com cantos suavemente arredondados no hover**:
  - A cápsula da Top Bar substituiu o formato oval (`border-radius: 999px`) por um retângulo suavemente arredondado (`border-radius: 8px`), alinhado ao padrão oficial do Ubuntu System Tray.
  - No hover, ativa o realce sutil do Ubuntu (`box-shadow: inset 0 0 0 100px rgba(255, 255, 255, 0.14)`), mantendo repouso 100% transparente.
- **Simplificação para 2 estágios essenciais**:
  - Estágio 1: Pílula Estável na Top Bar (Data/Hora unificada ao modelo ativo).
  - Estágio 2: Dashboard Completo Glassmorphism translúcido ao clicar.
- **Versão atualizada**:
  - `extension/metadata.json` atualizado para `version: 7` e `version-name: "1.3.0"`.

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
