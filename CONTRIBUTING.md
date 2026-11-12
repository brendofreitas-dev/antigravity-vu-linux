# Guia de Contribuição — Antigravity View Usage

Agradecemos imensamente seu interesse em contribuir com o **Antigravity View Usage**! Este projeto é construído pela comunidade para desenvolvedores que utilizam o Google Antigravity e desejam a melhor experiência visual e de telemetria no ecossistema Linux.

---

## 📋 Código de Conduta

Ao participar deste projeto, você se compromete a manter um ambiente acolhedor, respeitoso e profissional para todos, independentemente de experiência, identidade ou opiniões técnicas.

---

## 🛠️ Configuração do Ambiente de Desenvolvimento

### Pré-requisitos
- Distribuição Linux com **GNOME Shell 45 ou superior** (GNOME 45 a 50+).
- **Python 3.10+** (utiliza bibliotecas padrão do Python: `urllib`, `sqlite3`, `json`, `datetime`, `os`, `sys`).
- **GJS** (GNOME JavaScript Engine) e utilitário `gnome-extensions`.

### 1. Clonando o Repositório
```bash
git clone https://github.com/brendo-freitas/antigravity-vU-linux.git
cd antigravity-vU-linux
```

### 2. Testando o Coletor de Telemetria Localmente
O coletor não necessita de instalação de pacotes via pip:

```bash
# Executar a saída formatada de terminal
python3 backend/ag_vu_collector.py --pretty

# Executar a saída JSON bruta
python3 backend/ag_vu_collector.py --json

# Testar o modo de monitoramento contínuo
python3 backend/ag_vu_collector.py --watch
```

### 3. Executando a Suíte de Testes
Todos os testes unitários utilizam o módulo padrão `unittest`:

```bash
python3 -m unittest discover -s tests -p "test_*.py" -v
```

### 4. Instalando e Depurando a Extensão em Modo Desenvolvimento
Para testar alterações na extensão em tempo real:

1. Crie um link simbólico da pasta `extension/` para o diretório de extensões do GNOME:
   ```bash
   mkdir -p ~/.local/share/gnome-shell/extensions
   ln -s "$(pwd)/extension" ~/.local/share/gnome-shell/extensions/antigravity-vu@brendo.freitas
   ```
2. Habilite a extensão:
   ```bash
   gnome-extensions enable antigravity-vu@brendo.freitas
   ```
3. Acompanhe os logs do GNOME Shell em tempo real no terminal:
   ```bash
   journalctl -f -o cat /usr/bin/gnome-shell
   ```
4. Utilize o **Looking Glass** do GNOME Shell para inspecionar a hierarquia de atores e testar comandos GJS:
   - Pressione `Alt + F2`, digite `lg` e tecle Enter.
   - Para recarregar a sessão no X11: `Alt + F2` -> `r` -> Enter.
   - No Wayland, faça logout/login ou reinicie a sessão para testar novos arquivos de metadados.

---

## 📐 Diretrizes e Padrões de Código

### Python (`backend/`)
- Siga as convenções da **PEP 8**.
- **Regra de Ouro**: O coletor deve manter **zero dependências externas**. Não adicione pacotes ao `requirements.txt` sem discussão prévia de arquitetura.
- **Timeouts Rígidos**: Qualquer operação de rede local (ConnectRPC) deve ter timeout estrito (`timeout <= 1.5s`).
- **SQLite Seguro**: Sempre abra o banco `conversation_summaries.db` em modo somente leitura (`mode=ro`) para nunca bloquear a escrita da IDE.

### JavaScript / GJS (`extension/`)
- Utilize exclusivamente **ECMAScript Modules (ESM)** nativos (`import ... from 'gi://...'` e `resource:///org/gnome/shell/...`). Nunca utilize o padrão legado `const ... = imports.ui`.
- **Desalocação Completa no `disable()`**: Qualquer timer registrado via `GLib.timeout_add` deve ser cancelado com `GLib.source_remove()`. Todos os sinais conectados devem ser desconectados para evitar vazamentos de memória (*memory leaks*).
- **Zero Bloqueio**: Toda chamada de I/O ou execução de comandos deve utilizar `Gio.Subprocess` com comunicação assíncrona (`communicate_utf8_async`).

### Estilo Visual & CSS (`stylesheet.css`)
- Siga as diretrizes de design do projeto baseadas no padrão **Dark Glassmorphism / OLED Dark**.
- Utilize seletores específicos de classe (ex: `.ag-island-pill`, `.ag-island-popup`) para evitar colisões com o tema global do GNOME Shell.

---

## 📝 Padrão de Commits

Adotamos a especificação de [Conventional Commits](https://www.conventionalcommits.org/pt-br/v1.0.0/):

- `feat:` Nova funcionalidade para o usuário ou CLI.
- `fix:` Correção de bug no coletor ou na extensão.
- `docs:` Alterações na documentação, README ou diagramas.
- `perf:` Melhoria de performance (tempo de resposta, consumo de memória).
- `test:` Adição ou correção de testes unitários.
- `refactor:` Alteração no código que não adiciona recurso nem corrige bug.
- `chore:` Tarefas de manutenção ou atualização de metadados.

*Exemplo*: `feat(extension): adicionar suporte a expansão dinâmica no hover`

---

## 🚀 Processo de Envio de Pull Request

1. Faça um Fork do repositório.
2. Crie uma branch para sua funcionalidade ou correção:
   ```bash
   git checkout -b feature/minha-melhoria
   ```
3. Execute a suíte de testes e garanta que todos os testes passaram:
   ```bash
   python3 -m unittest discover -s tests
   ```
4. Faça o commit das suas alterações seguindo o padrão de commits.
5. Envie a branch para o seu repositório no GitHub:
   ```bash
   git push origin feature/minha-melhoria
   ```
6. Abra um **Pull Request** detalhando as mudanças realizadas, screenshots/GIFs (se houver alteração visual) e o problema solucionado.

Muito obrigado por ajudar a tornar o **Antigravity View Usage** ainda melhor!
