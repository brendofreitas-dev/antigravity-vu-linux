# Roadmap — Antigravity View Usage

Este documento traça o planejamento estratégico e a evolução do projeto **Antigravity View Usage** ao longo das próximas versões.

---

## 🗺️ Visão Geral dos Marcos

```mermaid
flowchart LR
    v10["v1.0.0<br/>• Dynamic Island GNOME<br/>• Quotas ConnectRPC<br/>• Swarm Tracker<br/>• CLI ag-vu"]
    v11["v1.1.0 – v1.3.1<br/>• Unified Island & Theme<br/>• Active Model Auto Quota<br/>• System Tray Hover"]
    v14["v1.4.0 (Atual) ✅<br/>• Dashboard 2 Colunas (720px)<br/>• Legenda de Cores 2×2<br/>• Swarm Completo sem Scroll"]
    v15["v1.5.0 (Q1 2027)<br/>• Painel Prefs GTK4/Adw<br/>• Alertas de Cota Crítica<br/>• Gráficos Sparkline Cairo"]
    v20["v2.0.0 (Q3 2027)<br/>• Multi-Account Switcher<br/>• Estimador de Custos<br/>• Histórico Anual SQLite"]

    v10 --> v11 --> v14 --> v15 --> v20
```

---

## 📌 Versões Planejadas

### [v1.0.0] — Lançamento Inicial (Atual) ✅
- [x] Extensão GNOME Shell 45-50+ com arquitetura ESM pura.
- [x] Integração na Top Bar ao lado do `DateMenu` nativo sem alterar relógio ou calendário.
- [x] 3 estágios da Dynamic Island: pílula compacta (28px), expansão em hover e dashboard Glassmorphism.
- [x] Coletor de telemetria autônomo em Python 3 (`ag-vu`) com zero dependências externas.
- [x] Descoberta automática de instâncias do Antigravity Language Server via ConnectRPC.
- [x] Monitor de cotas em tempo real: Gemini 4 Argon, Gemini Models e Claude/GPT 3P.
- [x] Leitura de sessões e árvores de agentes do Swarm (`conversation_summaries.db`).
- [x] Indexador incremental de transcripts com cache baseado em `mtime_ns`.
- [x] CLI com modos `--pretty`, `--json`, `--watch` e `--pin-group`.
- [x] Scripts de instalação (`install.sh`) e desinstalação (`uninstall.sh`).

---

### [v1.1.0] — Unified Island & Tema Adaptativo ✅ (2026-11-12)
- [x] **Unified Dynamic Island (Date/Time + Antigravity)**: cápsula única sobre `_centerBox`, calendário nativo preservado, reversível no `disable()`.
- [x] **Adaptive Ubuntu System Theme (Light/Dark)** com cores de acento Yaru/Adwaita.
- [x] Fix do `PopupMenu` (colapso de altura no GNOME 50).

### [v1.3.0] — Refinamento de UX & Simplificação da Dynamic Island ✅ (2026-11-12)
- [x] **Simplificação para 2 Estágios**: remoção do hover expansivo na Top Bar para um indicador estável, limpo e direto.
- [x] **Automação Completa da Cota Primária**: remoção dos botões manuais `📌 Fixar`; a Top Bar acompanha dinamicamente o modelo em uso na IDE.
- [x] **Retângulo com Cantos Arredondados no Hover**: transição do formato oval para retângulo arredondado (`border-radius: 8px`), alinhado ao padrão dos botões da Top Bar do Ubuntu Yaru.
- [x] **Legenda de Cores no Dashboard**: inclusão de componente `.ag-color-legend` com significado das cores Verde, Âmbar, Vermelho e Azul.
- [x] **Visual Translúcido Calendar**: herança direta de `.popup-menu-content` nativo sem caixas rígidas.

---

### [v1.4.0] — Dashboard em 2 Colunas & Grade de Legenda ✅ (2026-11-13)
- [x] **Dashboard em 2 Colunas (720px)**: layout equilibrado estilo Ubuntu Calendar com divisão lógica de seções.
- [x] **Coluna Esquerda (345px)**: Cotas de modelos (barras de 310px), Legenda da pílula 2×2 e Sessão Ativa.
- [x] **Coluna Direita (335px)**: Agentes do Swarm sem corte vertical e Consumo no Mês / Top Projetos.
- [x] **Legenda da Pílula em Grade 2×2**: pontos reais `St.Widget` alinhados e espaçados harmoniosamente.
- [x] **Remoção de Scroll nos Agentes**: visualização direta de todos os agentes sem barras cinzentas de rolagem.

---

### [v1.5.0] — Experiência do Usuário & Alertas Nativos 🎯 (Q1 2027)
- [ ] **Interface Gráfica de Configuração (`prefs.js`)**:
  - Diálogo nativo em GTK4 / Libadwaita integrado ao aplicativo *Extensões* do GNOME.
  - Seleção visual do grupo de cota fixado na pílula.
  - Ajuste deslizante do intervalo de atualização (2s a 30s).
- [ ] **Notificações de Cota Crítica**:
  - Alerta nativo do sistema quando qualquer cota cair abaixo de 10% ou 5%.
  - Notificação de aviso 30 minutos antes do reset semanal.
- [ ] **Mini-Gráficos Sparkline em Cairo**:
  - Renderização vetorial leve de sparkline da velocidade de tokens nos últimos 30 minutos.
- [ ] **Atalhos de Teclado Globais**:
  - Atalho configurável (ex: `Super + Shift + A`) para alternar a exibição da Dynamic Island ou abrir o dashboard.

---

### [v1.3.0] — Ecossistema Wayland & Extensibilidade 🌐
- [ ] **Modo Floating Overlay (Wayland Layer Shell)**:
  - Aplicação independente em Python/GTK4 ou Rust para ambientes que não utilizam GNOME Shell (Hyprland, Sway, KDE Plasma 6).
- [ ] **Exportador de Métricas para Prometheus / Grafana**:
  - Flag CLI `ag-vu --serve-metrics :9100` expondo métricas de cota e tokens no formato padrão do Prometheus.
- [ ] **Suporte a Plugins e Custom Hooks**:
  - Capacidade de acionar scripts personalizados ao ocorrer eventos (ex: alertar canal do Discord/Slack quando o swarm finalizar uma tarefa).

---

### [v2.0.0] — Inteligência Financeira & Gestão Avançada 🚀
- [ ] **Multi-Conta & Troca Rápida de Perfil**:
  - Suporte a múltiplos perfis de login do Google Cloud / Antigravity com comutação via menu.
- [ ] **Estimativa Financeira e Economia de Prompt Cache**:
  - Cálculo estimativo de economia financeira obtida através dos tokens lidos de prompt cache vs chamadas diretas.
- [ ] **Histórico Temporal em Banco Dedicado**:
  - Armazenamento de telemetria histórica em SQLite local para geração de relatórios de consumo mensal, semanal e diário.

---

*Sugestões e pedidos de novas funcionalidades podem ser abertos na seção de Issues do repositório!*
