/* island.js
 * Antigravity Unified Dynamic Island Implementation
 * Supports Hot-Reload, Adaptive Ubuntu Yaru Theme (Dark/Light + Accents)
 *
 * Copyright (C) 2026 Brendo Freitas
 * SPDX-License-Identifier: MIT
 */

import Clutter from 'gi://Clutter';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import GObject from 'gi://GObject';
import St from 'gi://St';

import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';
import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';

const POLL_INTERVAL_SECONDS = 5;

function createVBox(styleClass = null, spacing = 0) {
    const box = new St.BoxLayout({
        vertical: true,
        x_expand: true,
    });
    if (Clutter.Orientation) {
        box.orientation = Clutter.Orientation.VERTICAL;
    }
    if (styleClass) {
        box.add_style_class_name(styleClass);
    }
    if (spacing > 0) {
        box.spacing = spacing;
    }
    return box;
}

function createHBox(styleClass = null, spacing = 0) {
    const box = new St.BoxLayout({
        vertical: false,
        x_expand: true,
        y_align: Clutter.ActorAlign.CENTER,
    });
    if (Clutter.Orientation) {
        box.orientation = Clutter.Orientation.HORIZONTAL;
    }
    if (styleClass) {
        box.add_style_class_name(styleClass);
    }
    if (spacing > 0) {
        box.spacing = spacing;
    }
    return box;
}

function formatShortGroupName(groupName, groupId, activeModel = null) {
    if (!groupName && !groupId) return '⚡';
    const raw = (groupName || '').replace(/\u00a0/g, ' ').trim();
    if (raw === '4 Hydrogen' || raw === 'Gemini 3.8' || raw === '4 Argon' || raw === 'Claude/GPT') {
        return raw;
    }

    const gid = (groupId || '').toLowerCase();
    const gname = raw.toLowerCase();
    const am = (activeModel || '').toLowerCase();

    if (am.includes('hydrogen')) {
        return '4 Hydrogen';
    }
    if (am.includes('flash') || am.includes('gemini-3.8') || am.includes('3.8')) {
        return 'Gemini 3.8';
    }
    if (am.includes('argon')) {
        return '4 Argon';
    }
    if (am.includes('claude') || am.includes('gpt') || am.includes('opus') || am.includes('sonnet')) {
        return 'Claude/GPT';
    }

    if (gid === 'hydrogen' || (gname.includes('hydrogen') && !gname.includes('3.8') && !gname.includes('flash'))) {
        return '4 Hydrogen';
    }
    if (gid === 'gemini' || gname.includes('gemini 3.8') || gname.includes('gemini models') || (gname.includes('gemini') && !gname.includes('argon'))) {
        if (gname.includes('hydrogen') && !gname.includes('flash') && !gname.includes('3.8')) {
            return '4 Hydrogen';
        }
        return 'Gemini 3.8';
    }
    if (gid === 'argon' || gname.includes('argon')) {
        return '4 Argon';
    }
    if (gid === '3p' || gname.includes('claude') || gname.includes('gpt')) {
        return 'Claude/GPT';
    }

    return raw
        .replace(/gemini/i, '')
        .replace(/models/i, '')
        .replace(/and/i, '')
        .replace(/gpt/i, '')
        .trim() || '⚡';
}

function formatDisplayGroupName(group) {
    const gid = (group.id || '').toLowerCase();
    const gname = (group.name || '').replace(/\u00a0/g, ' ').toLowerCase();

    if (gid === 'hydrogen' || (gname.includes('hydrogen') && !gname.includes('gemini 3.8') && !gname.includes('flash'))) {
        return 'Gemini 4 Hydrogen';
    }
    if (gid === 'gemini' || gname.includes('gemini models') || gname.includes('gemini 3.8') || gname.includes('hydrogen')) {
        return 'Gemini 3.8 Flash & 4 Hydrogen';
    }
    if (gid === 'argon' || gname.includes('argon')) {
        return 'Gemini 4 Argon';
    }
    if (gid === '3p' || gname.includes('claude') || gname.includes('gpt')) {
        return 'Claude & GPT (Opus / Sonnet / GPT)';
    }
    return group.name;
}

function resolveCollectorCmd(extensionPath) {
    const home = GLib.get_home_dir();
    const localBin = GLib.build_filenamev([home, '.local', 'bin', 'ag-vu']);

    let cmd = null;
    if (GLib.file_test(localBin, GLib.FileTest.IS_EXECUTABLE)) {
        cmd = [localBin];
    } else {
        const inPath = GLib.find_program_in_path('ag-vu');
        if (inPath) {
            cmd = [inPath];
        } else {
            const defaultBackend = GLib.build_filenamev([
                home, 'Projetos', 'antigravity-vU-linux', 'backend', 'ag_vu_collector.py'
            ]);
            if (GLib.file_test(defaultBackend, GLib.FileTest.EXISTS)) {
                cmd = ['python3', defaultBackend];
            } else if (extensionPath) {
                const extDir = Gio.File.new_for_path(extensionPath);
                const parentDir = extDir.get_parent();
                if (parentDir) {
                    const fallbackPath = GLib.build_filenamev([
                        parentDir.get_path(), 'backend', 'ag_vu_collector.py'
                    ]);
                    if (GLib.file_test(fallbackPath, GLib.FileTest.EXISTS)) {
                        cmd = ['python3', fallbackPath];
                    }
                }
            }
        }
    }

    if (!cmd) {
        cmd = ['python3', GLib.build_filenamev([home, 'Projetos', 'antigravity-vU-linux', 'backend', 'ag_vu_collector.py'])];
    }

    cmd.push('--json');
    return cmd;
}

export const AntigravityIndicator = GObject.registerClass({
    GTypeName: 'AntigravityUnifiedIndicator'
}, class AntigravityUnifiedIndicator extends PanelMenu.Button {
    _init(extension) {
        super._init(0.0, 'AntigravityUnifiedIndicator', false);

        this._extension = extension;
        this._cancellable = new Gio.Cancellable();
        this._timerId = 0;
        this._lastData = null;
        this._isRefreshing = false;

        this._centerBoxHoverId = 0;
        this._dateMenuHoverId = 0;
        this._selfHoverId = 0;
        this._menuStateId = 0;
        this._dateMenuStateId = 0;

        this.add_style_class_name('ag-panel-button');
        this.add_style_class_name('ag-unified-island-indicator');
        this.y_align = Clutter.ActorAlign.CENTER;
        this.y_expand = true;
        this.track_hover = true;

        this._buildPill();
        this._buildMenuShell();

        // Connect menu state to re-render when opening
        this.menu.connect('open-state-changed', (menu, isOpen) => {
            if (isOpen) {
                this._renderMenuContent();
            }
        });

        // Initialize and listen to desktop theme changes (Light/Dark + Accent Color)
        this._initThemeListener();

        // Integrate with Main.panel._centerBox to form the Unified Dynamic Island Capsule
        this._integrateUnifiedIsland();

        // Initial fetch
        this._fetchData();

        // Start periodic background polling
        this._timerId = GLib.timeout_add_seconds(
            GLib.PRIORITY_DEFAULT,
            POLL_INTERVAL_SECONDS,
            () => {
                this._fetchData();
                return GLib.SOURCE_CONTINUE;
            }
        );
    }

    _buildPill() {
        this._pillBox = createHBox('ag-island-pill', 6);
        this._pillBox.reactive = true;
        this._pillBox.can_focus = true;
        this._pillBox.y_align = Clutter.ActorAlign.CENTER;
        this._pillBox.y_expand = true;

        // Status glowing dot
        this._statusDot = new St.Widget({
            style_class: 'ag-dot ag-dot-healthy',
            y_align: Clutter.ActorAlign.CENTER,
        });
        this._pillBox.add_child(this._statusDot);

        // Quota percentage label (Closed mode)
        this._quotaLabel = new St.Label({
            text: '⚡ --%',
            style_class: 'ag-pill-quota',
            y_align: Clutter.ActorAlign.CENTER,
            y_expand: true,
        });
        this._pillBox.add_child(this._quotaLabel);

        this.add_child(this._pillBox);
    }

    _buildMenuShell() {
        this._menuSection = new PopupMenu.PopupMenuSection();
        this._contentBox = createVBox('ag-popup-menu');

        const container = this._menuSection.actor || this._menuSection;
        container.add_child(this._contentBox);
        this.menu.addMenuItem(this._menuSection);
    }

    /* =========================================================================
       Unified Dynamic Island Capsule Management (Date/Time + Antigravity)
       ========================================================================= */

    _integrateUnifiedIsland() {
        this._centerBox = Main.panel._centerBox;
        if (this._centerBox) {
            this._centerBox.add_style_class_name('ag-unified-island-capsule');
            this._centerBox.reactive = true;
            this._centerBox.track_hover = true;

            this._centerBoxHoverId = this._centerBox.connect('notify::hover', () => this._syncCapsuleHover());
        }

        // Add class to dateMenu for seamless pill edge and divider
        this._dateMenu = Main.panel.statusArea.dateMenu || Main.panel._dateMenu;
        if (this._dateMenu) {
            this._dateMenu.add_style_class_name('ag-unified-island-date');
            this._dateMenu.reactive = true;
            this._dateMenu.track_hover = true;

            this._dateMenuHoverId = this._dateMenu.connect('notify::hover', () => this._syncCapsuleHover());
            if (this._dateMenu.menu) {
                this._dateMenuStateId = this._dateMenu.menu.connect('open-state-changed', () => this._syncCapsuleHover());
            }
        }

        this.track_hover = true;
        this._selfHoverId = this.connect('notify::hover', () => this._syncCapsuleHover());
        if (this.menu) {
            this._menuStateId = this.menu.connect('open-state-changed', () => this._syncCapsuleHover());
        }

        this._applyTheme();
    }

    _syncCapsuleHover() {
        if (!this._centerBox) return;

        const isHovered = !!(
            (this._centerBox && this._centerBox.hover) ||
            (this._dateMenu && this._dateMenu.hover) ||
            this.hover ||
            (this.menu && this.menu.isOpen) ||
            (this._dateMenu && this._dateMenu.menu && this._dateMenu.menu.isOpen)
        );

        if (isHovered) {
            this._centerBox.add_style_class_name('ag-capsule-hovered');
        } else {
            this._centerBox.remove_style_class_name('ag-capsule-hovered');
        }
    }

    _removeUnifiedIsland() {
        if (this._centerBox) {
            if (this._centerBoxHoverId) {
                this._centerBox.disconnect(this._centerBoxHoverId);
                this._centerBoxHoverId = 0;
            }
            this._centerBox.remove_style_class_name('ag-capsule-hovered');
            this._centerBox.remove_style_class_name('ag-unified-island-capsule');
            this._centerBox.remove_style_class_name('ag-theme-dark');
            this._centerBox.remove_style_class_name('ag-theme-light');
            this._removeAllAccentClasses(this._centerBox);
        }

        if (this._dateMenu) {
            if (this._dateMenuHoverId) {
                this._dateMenu.disconnect(this._dateMenuHoverId);
                this._dateMenuHoverId = 0;
            }
            if (this._dateMenuStateId && this._dateMenu.menu) {
                this._dateMenu.menu.disconnect(this._dateMenuStateId);
                this._dateMenuStateId = 0;
            }
            this._dateMenu.remove_style_class_name('ag-unified-island-date');
        }

        if (this._selfHoverId) {
            this.disconnect(this._selfHoverId);
            this._selfHoverId = 0;
        }

        if (this._menuStateId && this.menu) {
            this.menu.disconnect(this._menuStateId);
            this._menuStateId = 0;
        }

        if (this.menu && this.menu.box) {
            this.menu.box.remove_style_class_name('ag-theme-dark');
            this.menu.box.remove_style_class_name('ag-theme-light');
        }
    }

    /* =========================================================================
       Theme Detection & Adaptation (Light/Dark + Ubuntu Accent Colors)
       ========================================================================= */

    _initThemeListener() {
        try {
            this._desktopSettings = new Gio.Settings({ schema_id: 'org.gnome.desktop.interface' });
            this._settingsChangedId = this._desktopSettings.connect('changed', (settings, key) => {
                if (key === 'color-scheme' || key === 'gtk-theme' || key === 'accent-color') {
                    this._applyTheme();
                }
            });
        } catch (e) {
            console.warn(`[Antigravity-vU] Could not listen to desktop interface settings: ${e.message}`);
        }

        try {
            this._themeContext = St.ThemeContext.get_for_stage(global.stage);
            this._themeContextChangedId = this._themeContext.connect('changed', () => {
                this._applyTheme();
            });
        } catch (e) {}
    }

    _applyTheme() {
        let isDark = true;
        let accent = 'blue';

        if (this._desktopSettings) {
            try {
                const colorScheme = this._desktopSettings.get_string('color-scheme');
                if (colorScheme === 'prefer-light') {
                    isDark = false;
                } else if (colorScheme === 'prefer-dark') {
                    isDark = true;
                } else {
                    const gtkTheme = this._desktopSettings.get_string('gtk-theme').toLowerCase();
                    isDark = gtkTheme.includes('-dark') || gtkTheme.includes('dark');
                }
            } catch (e) {
                isDark = true;
            }

            try {
                accent = this._desktopSettings.get_string('accent-color') || 'blue';
            } catch (e) {
                accent = 'blue';
            }
        }

        const themeClass = isDark ? 'ag-theme-dark' : 'ag-theme-light';
        const accentClass = `ag-accent-${accent}`;

        // 1. CenterBox Capsule
        if (this._centerBox) {
            this._centerBox.remove_style_class_name('ag-theme-dark');
            this._centerBox.remove_style_class_name('ag-theme-light');
            this._removeAllAccentClasses(this._centerBox);

            this._centerBox.add_style_class_name(themeClass);
            this._centerBox.add_style_class_name(accentClass);
        }

        // 2. Popup Menu Box (outer container of this.menu)
        if (this.menu && this.menu.box) {
            this.menu.box.remove_style_class_name('ag-theme-dark');
            this.menu.box.remove_style_class_name('ag-theme-light');
            this.menu.box.add_style_class_name(themeClass);
        }

        // 3. Content Box
        if (this._contentBox) {
            this._contentBox.remove_style_class_name('ag-theme-dark');
            this._contentBox.remove_style_class_name('ag-theme-light');
            this._removeAllAccentClasses(this._contentBox);

            this._contentBox.add_style_class_name(themeClass);
            this._contentBox.add_style_class_name(accentClass);
        }
    }

    _removeAllAccentClasses(actor) {
        const accents = ['blue', 'teal', 'green', 'yellow', 'orange', 'red', 'pink', 'purple', 'slate'];
        for (const a of accents) {
            actor.remove_style_class_name(`ag-accent-${a}`);
        }
    }

    /* =========================================================================
       Data Fetching & Subprocess Communication
       ========================================================================= */

    _fetchData(isManualRefresh = false) {
        if (this._isRefreshing && !isManualRefresh) {
            return;
        }

        this._isRefreshing = true;
        const cmd = resolveCollectorCmd(this._extension.path);

        try {
            const proc = Gio.Subprocess.new(
                cmd,
                Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_PIPE
            );

            proc.communicate_utf8_async(null, this._cancellable, (p, res) => {
                this._isRefreshing = false;
                try {
                    const [, stdout, stderr] = p.communicate_utf8_finish(res);
                    if (p.get_successful()) {
                        const data = JSON.parse(stdout);
                        this._lastData = data;
                        this._updatePill(data);
                        if (this.menu.isOpen) {
                            this._renderMenuContent();
                        }
                    } else {
                        console.warn(`[Antigravity-vU] Collector error: ${stderr || stdout}`);
                    }
                } catch (err) {
                    if (!err.matches(Gio.IOErrorEnum, Gio.IOErrorEnum.CANCELLED)) {
                        console.warn(`[Antigravity-vU] JSON parse or read error: ${err.message}`);
                    }
                }
            });
        } catch (e) {
            this._isRefreshing = false;
            console.warn(`[Antigravity-vU] Failed to spawn collector: ${e.message}`);
        }
    }

    _updatePill(data) {
        if (!data) return;

        const isWorking = !!(data.swarm?.is_working);

        // Update dot status class
        this._statusDot.remove_style_class_name('ag-dot-working');
        this._statusDot.remove_style_class_name('ag-dot-healthy');
        this._statusDot.remove_style_class_name('ag-dot-warning');
        this._statusDot.remove_style_class_name('ag-dot-critical');

        let remainingPct = 100;
        let quotaLabelText = '⚡ --%';

        const activeModel = data.active_context?.active_model || '';

        if (data.primary_quota) {
            remainingPct = data.primary_quota.remaining_pct;
            const shortName = formatShortGroupName(
                data.primary_quota.pill_name || data.primary_quota.group,
                data.primary_quota.id || data.primary_quota.group_id,
                activeModel
            );
            quotaLabelText = `${shortName} ${Math.round(remainingPct)}%`;
        }

        if (isWorking) {
            this._statusDot.add_style_class_name('ag-dot-working');
        } else if (remainingPct < 20) {
            this._statusDot.add_style_class_name('ag-dot-critical');
        } else if (remainingPct < 50) {
            this._statusDot.add_style_class_name('ag-dot-warning');
        } else {
            this._statusDot.add_style_class_name('ag-dot-healthy');
        }

        this._quotaLabel.text = quotaLabelText;
    }

    _renderMenuContent() {
        const data = this._lastData;
        this._contentBox.destroy_all_children();

        if (!data) {
            const loadingBox = createVBox('ag-context-card', 6);
            loadingBox.style = 'padding: 16px;';

            const emptyLabel = new St.Label({
                text: 'Carregando métricas do Antigravity...',
                style_class: 'ag-header-title',
                x_align: Clutter.ActorAlign.CENTER,
            });
            loadingBox.add_child(emptyLabel);

            const hintLabel = new St.Label({
                text: 'Coletando quotas, tokens e swarm em segundo plano...',
                style_class: 'ag-session-title',
                x_align: Clutter.ActorAlign.CENTER,
            });
            loadingBox.add_child(hintLabel);

            this._contentBox.add_child(loadingBox);
            return;
        }

        // ================= 1. HEADER =================
        const headerBox = createHBox('ag-header-box');
        headerBox.x_expand = true;

        const titleLabel = new St.Label({
            text: 'Antigravity View Usage',
            style_class: 'ag-header-title',
            x_expand: true,
            y_align: Clutter.ActorAlign.CENTER,
        });
        headerBox.add_child(titleLabel);

        const metaBox = createHBox('ag-header-meta', 10);
        metaBox.x_expand = false;
        metaBox.x_align = Clutter.ActorAlign.END;
        metaBox.y_align = Clutter.ActorAlign.CENTER;

        const tierBadge = new St.Label({
            text: data.user?.tier || 'Pro',
            style_class: 'ag-tier-badge',
            y_align: Clutter.ActorAlign.CENTER,
        });
        metaBox.add_child(tierBadge);

        const onlineBadge = new St.Label({
            text: data.user?.ls_online ? '● Online' : '● Offline',
            style_class: data.user?.ls_online ? 'ag-online-badge' : 'ag-offline-badge',
            y_align: Clutter.ActorAlign.CENTER,
        });
        metaBox.add_child(onlineBadge);

        const refreshBtn = new St.Button({
            label: '↻',
            style_class: 'ag-btn-refresh',
            can_focus: true,
            y_align: Clutter.ActorAlign.CENTER,
        });
        refreshBtn.connect('clicked', () => {
            refreshBtn.label = '⏳';
            this._fetchData(true);
        });
        metaBox.add_child(refreshBtn);

        headerBox.add_child(metaBox);
        this._contentBox.add_child(headerBox);

        // ================= 2-COLUMN BALANCED CONTAINER =================
        const columnsBox = createHBox('ag-columns-box', 14);
        columnsBox.y_align = Clutter.ActorAlign.START;
        columnsBox.x_expand = true;

        const leftCol = createVBox('ag-col-left');
        leftCol.y_align = Clutter.ActorAlign.START;
        leftCol.x_expand = false;

        const rightCol = createVBox('ag-col-right');
        rightCol.y_align = Clutter.ActorAlign.START;
        rightCol.x_expand = false;

        columnsBox.add_child(leftCol);
        columnsBox.add_child(rightCol);
        this._contentBox.add_child(columnsBox);

        // ================= LEFT COLUMN: 1. QUOTAS =================
        const quotaTitle = new St.Label({
            text: '📊 Quotas & Limites dos Modelos',
            style_class: 'ag-section-title',
        });
        leftCol.add_child(quotaTitle);

        if (Array.isArray(data.quota_groups)) {
            for (const group of data.quota_groups) {
                const groupCard = createVBox('ag-group-card');

                const groupHeader = createHBox();

                const displayName = formatDisplayGroupName(group);
                const groupNameLabel = new St.Label({
                    text: displayName,
                    style_class: 'ag-group-name',
                    x_expand: true,
                    y_align: Clutter.ActorAlign.CENTER,
                });
                groupHeader.add_child(groupNameLabel);
                groupCard.add_child(groupHeader);

                if (group.description) {
                    const descLabel = new St.Label({
                        text: group.description,
                        style_class: 'ag-group-desc',
                    });
                    groupCard.add_child(descLabel);
                }

                if (Array.isArray(group.buckets)) {
                    for (const bucket of group.buckets) {
                        const bucketRow = createHBox('ag-bucket-row');

                        const bucketLabel = new St.Label({
                            text: bucket.label || bucket.id,
                            style_class: 'ag-bucket-label',
                            x_expand: true,
                        });
                        bucketRow.add_child(bucketLabel);

                        const pct = Number(bucket.remaining_pct || 0);
                        const metaLabel = new St.Label({
                            text: `${pct.toFixed(1)}% • ${bucket.reset_in || '--'}`,
                            style_class: 'ag-bucket-meta',
                        });
                        bucketRow.add_child(metaLabel);
                        groupCard.add_child(bucketRow);

                        // Visual progress bar (max 310px to fit 345px col)
                        const track = createHBox('ag-bar-track');

                        const fillWidth = Math.max(6, Math.round((pct / 100) * 310));
                        let fillClass = 'ag-bar-fill-healthy';
                        if (pct < 20) {
                            fillClass = 'ag-bar-fill-critical';
                        } else if (pct < 50) {
                            fillClass = 'ag-bar-fill-warning';
                        }

                        const fill = new St.Widget({
                            style_class: fillClass,
                            width: fillWidth,
                            height: 5,
                            x_expand: false,
                            y_expand: false,
                        });
                        track.add_child(fill);
                        groupCard.add_child(track);
                    }
                }

                leftCol.add_child(groupCard);
            }

            // ================= LEFT COLUMN: 2. DISCRETE 2x2 COLOR LEGEND =================
            const legendCard = createVBox('ag-color-legend', 4);

            const row1 = createHBox('ag-legend-row', 10);
            const cell1 = createHBox('ag-legend-cell', 6);
            cell1.x_expand = true;
            const dot1 = new St.Widget({ style_class: 'ag-legend-dot ag-dot-healthy' });
            const lbl1 = new St.Label({ text: '≥50% Normal', style_class: 'ag-legend-text' });
            cell1.add_child(dot1);
            cell1.add_child(lbl1);
            row1.add_child(cell1);

            const cell2 = createHBox('ag-legend-cell', 6);
            cell2.x_expand = true;
            const dot2 = new St.Widget({ style_class: 'ag-legend-dot ag-dot-warning' });
            const lbl2 = new St.Label({ text: '20–49% Atenção', style_class: 'ag-legend-text' });
            cell2.add_child(dot2);
            cell2.add_child(lbl2);
            row1.add_child(cell2);
            legendCard.add_child(row1);

            const row2 = createHBox('ag-legend-row', 10);
            const cell3 = createHBox('ag-legend-cell', 6);
            cell3.x_expand = true;
            const dot3 = new St.Widget({ style_class: 'ag-legend-dot ag-dot-critical' });
            const lbl3 = new St.Label({ text: '<20% Crítico', style_class: 'ag-legend-text' });
            cell3.add_child(dot3);
            cell3.add_child(lbl3);
            row2.add_child(cell3);

            const cell4 = createHBox('ag-legend-cell', 6);
            cell4.x_expand = true;
            const dot4 = new St.Widget({ style_class: 'ag-legend-dot ag-dot-working' });
            const lbl4 = new St.Label({ text: 'Agente Ativo', style_class: 'ag-legend-text' });
            cell4.add_child(dot4);
            cell4.add_child(lbl4);
            row2.add_child(cell4);
            legendCard.add_child(row2);

            leftCol.add_child(legendCard);
        }

        // ================= LEFT COLUMN: 3. ACTIVE SESSION =================
        const contextTitle = new St.Label({
            text: '⚡ Sessão Ativa',
            style_class: 'ag-section-title',
        });
        leftCol.add_child(contextTitle);

        const contextCard = createVBox('ag-context-card');

        const projName = data.active_context?.project_name || 'Fora de projeto';
        const projLabel = new St.Label({
            text: `📂 ${projName}`,
            style_class: 'ag-project-title',
        });
        contextCard.add_child(projLabel);

        const convTitle = data.active_context?.title || 'Sem sessão ativa';
        const convLabel = new St.Label({
            text: `💬 ${convTitle}`,
            style_class: 'ag-session-title',
        });
        contextCard.add_child(convLabel);

        if (data.active_context?.active_model_label) {
            const modelLabel = new St.Label({
                text: `🤖 ${data.active_context.active_model_label}`,
                style_class: 'ag-model-badge',
            });
            contextCard.add_child(modelLabel);
        }

        const totalTokensFormatted = data.active_context?.context_formatted || '0';
        const totalCtxLabel = new St.Label({
            text: `${totalTokensFormatted} tokens de contexto`,
            style_class: 'ag-context-total',
        });
        contextCard.add_child(totalCtxLabel);

        // Chips for In / Cache / Out
        const chipsBox = createHBox(null, 6);
        chipsBox.style = 'margin-top: 4px;';

        const inTokens = (data.active_context?.input_tokens || 0).toLocaleString();
        const inChip = new St.Label({
            text: `📥 In: ${inTokens}`,
            style_class: 'ag-chip',
        });
        chipsBox.add_child(inChip);

        const cacheTokens = (data.active_context?.cache_read_tokens || 0).toLocaleString();
        const cacheChip = new St.Label({
            text: `⚡ Cache: ${cacheTokens}`,
            style_class: 'ag-chip',
        });
        chipsBox.add_child(cacheChip);

        const outTokens = (data.active_context?.output_tokens || 0).toLocaleString();
        const outChip = new St.Label({
            text: `📤 Out: ${outTokens}`,
            style_class: 'ag-chip',
        });
        chipsBox.add_child(outChip);

        contextCard.add_child(chipsBox);
        leftCol.add_child(contextCard);

        // ================= RIGHT COLUMN: 1. SWARM AGENTS (NO SCROLLVIEW) =================
        const swarmActive = data.swarm?.active_count || 0;
        const swarmTotal = data.swarm?.total_alive || 0;
        const swarmHeading = new St.Label({
            text: `🤖 Agentes do Swarm (${swarmActive} ativos / ${swarmTotal} total):`,
            style_class: 'ag-section-title',
        });
        rightCol.add_child(swarmHeading);

        if (Array.isArray(data.swarm?.agents) && data.swarm.agents.length > 0) {
            const agentsContainer = createVBox(null, 2);

            for (const agent of data.swarm.agents) {
                const agentRow = createHBox('ag-agent-item', 6);

                const nameLabel = new St.Label({
                    text: agent.name,
                    style_class: 'ag-agent-name',
                    x_expand: true,
                    y_align: Clutter.ActorAlign.CENTER,
                });
                agentRow.add_child(nameLabel);

                const isWorking = !!(agent.is_working || agent.status === 'WORKING');
                const statusBadge = new St.Label({
                    text: isWorking ? 'WORKING' : 'IDLE',
                    style_class: isWorking ? 'ag-agent-status-working' : 'ag-agent-status-idle',
                    y_align: Clutter.ActorAlign.CENTER,
                });
                agentRow.add_child(statusBadge);

                const stepsLabel = new St.Label({
                    text: `${agent.steps || 0} steps`,
                    style_class: 'ag-agent-steps',
                    y_align: Clutter.ActorAlign.CENTER,
                });
                agentRow.add_child(stepsLabel);

                agentsContainer.add_child(agentRow);
            }

            rightCol.add_child(agentsContainer);
        } else {
            const noAgentsLabel = new St.Label({
                text: 'Nenhum subagente ativo no momento.',
                style_class: 'ag-session-title',
            });
            rightCol.add_child(noAgentsLabel);
        }

        // ================= RIGHT COLUMN: 2. MONTHLY CONSUMPTION & TOP PROJECTS =================
        const monthTitle = new St.Label({
            text: `📈 Consumo no Mês (${data.monthly_tokens?.month || '--'}) • Total: ${data.monthly_tokens?.total_formatted || '0'}`,
            style_class: 'ag-section-title',
        });
        rightCol.add_child(monthTitle);

        // 3 Cards layout
        const tokenCardsBox = createHBox(null, 6);

        const cards = [
            { title: 'INPUT', val: data.monthly_tokens?.input_formatted || '0' },
            { title: 'CACHE READ', val: data.monthly_tokens?.cache_formatted || '0' },
            { title: 'OUTPUT', val: data.monthly_tokens?.output_formatted || '0' },
        ];

        for (const card of cards) {
            const cBox = createVBox('ag-token-card');
            const tLabel = new St.Label({
                text: card.title,
                style_class: 'ag-token-title',
            });
            cBox.add_child(tLabel);

            const vLabel = new St.Label({
                text: card.val,
                style_class: 'ag-token-val',
            });
            cBox.add_child(vLabel);
            tokenCardsBox.add_child(cBox);
        }

        rightCol.add_child(tokenCardsBox);

        // Top Projects (show top 3)
        if (Array.isArray(data.projects) && data.projects.length > 0) {
            const projHeading = new St.Label({
                text: 'Top Projetos:',
                style_class: 'ag-section-title',
            });
            rightCol.add_child(projHeading);

            const topProjects = data.projects.slice(0, 3);
            for (const proj of topProjects) {
                const pBox = createVBox('ag-project-item');

                const pTop = createHBox();

                const pName = new St.Label({
                    text: proj.name,
                    style_class: 'ag-project-name',
                    x_expand: true,
                });
                pTop.add_child(pName);

                const pTotal = new St.Label({
                    text: proj.total_formatted || '0',
                    style_class: 'ag-project-tokens',
                });
                pTop.add_child(pTotal);
                pBox.add_child(pTop);

                const convCount = proj.conversations_count || 1;
                const pDetails = new St.Label({
                    text: `${convCount} sessões • In: ${proj.input_formatted} • Cache: ${proj.cache_formatted} • Out: ${proj.output_formatted}`,
                    style_class: 'ag-project-details',
                });
                pBox.add_child(pDetails);

                rightCol.add_child(pBox);
            }
        }

        // ================= 3. FOOTER =================
        const now = new Date();
        const timeStr = now.toLocaleTimeString();
        const verName = this._extension?.metadata?.['version-name'] || '1.4.0';
        const footerLabel = new St.Label({
            text: `Última atualização: ${timeStr} • Antigravity vU Linux v${verName}`,
            style_class: 'ag-footer-text',
            x_align: Clutter.ActorAlign.CENTER,
        });
        this._contentBox.add_child(footerLabel);
    }

    destroy() {
        if (this._timerId) {
            GLib.source_remove(this._timerId);
            this._timerId = 0;
        }

        if (this._settingsChangedId && this._desktopSettings) {
            this._desktopSettings.disconnect(this._settingsChangedId);
            this._settingsChangedId = 0;
        }

        if (this._themeContextChangedId && this._themeContext) {
            this._themeContext.disconnect(this._themeContextChangedId);
            this._themeContextChangedId = 0;
        }

        if (this._cancellable) {
            this._cancellable.cancel();
            this._cancellable = null;
        }

        this._removeUnifiedIsland();

        super.destroy();
    }
});

let currentIndicator = null;

export async function initIsland(extension) {
    currentIndicator = new AntigravityIndicator(extension);
    Main.panel.addToStatusArea(extension.uuid, currentIndicator, 1, 'center');
    return currentIndicator;
}

export function disableIsland() {
    if (currentIndicator) {
        currentIndicator.destroy();
        currentIndicator = null;
    }
}
