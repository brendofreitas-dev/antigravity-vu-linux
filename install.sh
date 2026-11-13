#!/usr/bin/env bash
# install.sh - Antigravity View Usage Dynamic Island Installer
# GNOME Shell 45 - 50 Extension & Backend CLI Setup

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

UUID="antigravity-vu@brendo.freitas"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXT_SRC="$SCRIPT_DIR/extension"
BACKEND_SRC="$SCRIPT_DIR/backend/ag_vu_collector.py"

EXT_DST="$HOME/.local/share/gnome-shell/extensions/$UUID"
BIN_DIR="$HOME/.local/bin"
BIN_TARGET="$BIN_DIR/ag-vu"
CONFIG_DIR="$HOME/.config/antigravity-vu"
PREFS_FILE="$CONFIG_DIR/prefs.json"

echo -e "${BLUE}======================================================${NC}"
echo -e "${BLUE}   Instalando Antigravity View Usage (Dynamic Island)   ${NC}"
echo -e "${BLUE}======================================================${NC}"

# 1. Verificar fontes da extensão
if [ ! -d "$EXT_SRC" ]; then
    echo -e "${RED}[ERRO] Diretório da extensão não encontrado: $EXT_SRC${NC}"
    exit 1
fi

# 2. Criar diretórios
echo -e "${BLUE}[1/5]${NC} Criando diretórios do usuário..."
mkdir -p "$EXT_DST"
mkdir -p "$BIN_DIR"
mkdir -p "$CONFIG_DIR"

# 3. Copiar arquivos da extensão GNOME
echo -e "${BLUE}[2/5]${NC} Copiando arquivos da extensão para $EXT_DST..."
cp -rv "$EXT_SRC/"* "$EXT_DST/"

if [ -d "$EXT_DST/schemas" ] && command -v glib-compile-schemas >/dev/null 2>&1; then
    echo -e "${BLUE}    Compilando schemas GSettings em $EXT_DST/schemas...${NC}"
    glib-compile-schemas "$EXT_DST/schemas"
fi

# 4. Configurar CLI backend ag-vu
echo -e "${BLUE}[3/5]${NC} Configurando CLI backend em $BIN_TARGET..."
if [ -f "$BACKEND_SRC" ]; then
    chmod +x "$BACKEND_SRC"
    ln -sf "$BACKEND_SRC" "$BIN_TARGET"
else
    # Cria wrapper executável que aponta para o backend
    cat << EOF > "$BIN_TARGET"
#!/usr/bin/env bash
exec python3 "$SCRIPT_DIR/backend/ag_vu_collector.py" "\$@"
EOF
    chmod +x "$BIN_TARGET"
fi

# 5. Criar preferências padrão caso não existam
echo -e "${BLUE}[4/5]${NC} Verificando preferências em $PREFS_FILE..."
if [ ! -f "$PREFS_FILE" ]; then
    cat << 'EOF' > "$PREFS_FILE"
{
  "pinned_group": "auto"
}
EOF
fi

# 6. Habilitar extensão via gnome-extensions e gsettings
echo -e "${BLUE}[5/5]${NC} Ativando extensão no GNOME Shell..."
if command -v gnome-extensions >/dev/null 2>&1; then
    gnome-extensions enable "$UUID" 2>/dev/null || true
fi

if command -v gsettings >/dev/null 2>&1; then
    CURRENT=$(gsettings get org.gnome.shell enabled-extensions 2>/dev/null || echo "")
    if [[ "$CURRENT" != *"$UUID"* ]]; then
        if [[ "$CURRENT" == "@as []" || "$CURRENT" == "[]" ]]; then
            gsettings set org.gnome.shell enabled-extensions "['$UUID']"
        elif [[ "$CURRENT" == *"]" ]]; then
            NEW=$(echo "$CURRENT" | sed "s/]/, '$UUID']/")
            gsettings set org.gnome.shell enabled-extensions "$NEW"
        fi
    fi
fi
echo -e "${GREEN}✓ Extensão configurada e habilitada no GNOME Shell!${NC}"

echo -e "\n${GREEN}======================================================${NC}"
echo -e "${GREEN}   Instalação concluída com sucesso! 🚀              ${NC}"
echo -e "${GREEN}======================================================${NC}"
echo -e "• Extensão instalada em: ${YELLOW}$EXT_DST${NC}"
echo -e "• CLI ag-vu disponível em: ${YELLOW}$BIN_TARGET${NC}"
echo -e "  (Certifique-se de que ~/.local/bin está no seu PATH)"
echo -e "• Para testar o CLI no terminal:"
echo -e "    ${BLUE}ag-vu --pretty${NC}"
echo -e "    ${BLUE}ag-vu --json${NC}"
echo -e "• No GNOME Shell Wayland: reinicie a sessão se for a primeira instalação."
echo -e "• No GNOME Shell X11: pressione Alt+F2, digite 'r' e Enter."
echo -e "${GREEN}======================================================${NC}"
