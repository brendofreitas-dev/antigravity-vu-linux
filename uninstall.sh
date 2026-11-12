#!/usr/bin/env bash
# uninstall.sh - Antigravity View Usage Dynamic Island Uninstaller
# Desinstalação limpa da Extensão GNOME Shell e CLI

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

UUID="antigravity-vu@brendo.freitas"
EXT_DST="$HOME/.local/share/gnome-shell/extensions/$UUID"
BIN_TARGET="$HOME/.local/bin/ag-vu"
CONFIG_DIR="$HOME/.config/antigravity-vu"
CACHE_DIR="$HOME/.cache/antigravity-vu"

echo -e "${YELLOW}======================================================${NC}"
echo -e "${YELLOW}   Desinstalando Antigravity View Usage...            ${NC}"
echo -e "${YELLOW}======================================================${NC}"

# 1. Desabilitar extensão se gnome-extensions ou gsettings estiverem disponíveis
if command -v gnome-extensions >/dev/null 2>&1; then
    echo -e "${BLUE}[1/4]${NC} Desabilitando extensão via gnome-extensions..."
    gnome-extensions disable "$UUID" 2>/dev/null || true
fi

if command -v gsettings >/dev/null 2>&1; then
    echo -e "${BLUE}[2/4]${NC} Removendo da lista de extensões ativas..."
    CURRENT=$(gsettings get org.gnome.shell enabled-extensions 2>/dev/null || echo "")
    if [[ "$CURRENT" == *"$UUID"* ]]; then
        NEW=$(echo "$CURRENT" | sed "s/'$UUID', //g; s/, '$UUID'//g; s/'$UUID'//g")
        gsettings set org.gnome.shell enabled-extensions "$NEW" 2>/dev/null || true
    fi
fi

# 2. Remover diretório da extensão
echo -e "${BLUE}[3/4]${NC} Removendo arquivos da extensão em $EXT_DST..."
rm -rf "$EXT_DST"

# 3. Remover binário
echo -e "${BLUE}[4/4]${NC} Removendo CLI ag-vu em $BIN_TARGET..."
rm -f "$BIN_TARGET"

# 4. Remover dados de configuração e cache se solicitado via --purge
if [[ "$1" == "--purge" ]]; then
    echo -e "${YELLOW}Limpando configurações e caches (~/.config e ~/.cache)...${NC}"
    rm -rf "$CONFIG_DIR"
    rm -rf "$CACHE_DIR"
fi

echo -e "\n${GREEN}======================================================${NC}"
echo -e "${GREEN}   Desinstalação concluída com sucesso!               ${NC}"
echo -e "${GREEN}======================================================${NC}"
echo -e "• A extensão e o CLI foram removidos do sistema."
if [[ "$1" != "--purge" ]]; then
    echo -e "• Suas preferências foram mantidas em $CONFIG_DIR."
    echo -e "  (Para remover tudo completamente, execute: ./uninstall.sh --purge)"
fi
