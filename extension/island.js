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
const AUTO_PEEK_DURATION_MS = 4000;

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

function formatShortGroupName(groupName, groupId) {
    if (!groupName && !groupId) return '⚡';
    const gid = (groupId || '').toLowerCase();
    const gname = (groupName || '').replace(/\u00a0/g, ' ').toLowerCase();

    if (gid === 'hydrogen' || gname.includes('hydrogen')) {
        return '4 Hydrogen';
    }
    if (gid === 'gemini' || gname.includes('gemini 3.8') || gname.includes('gemini models') || (gname.includes('gemini') && !gname.includes('argon'))) {
        return 'Gemini 3.8';
    }
    if (gid === 'argon' || gname.includes('argon')) {
        return '4 Argon';
    }
    if (gid === '3p' || gname.includes('claude') || gname.includes('gpt')) {
        return 'Claude/GPT';
    }

    return (groupName || '')
        .replace(/\u00a0/g, ' ')
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

function loadPrefs() {
    try {
        const configDir = GLib.build_filenamev([GLib.get_user_config_dir(), 'antigravity-vu']);
        const configFile = GLib.build_filenamev([configDir, 'prefs.json']);
        if (GLib.file_test(configFile, GLib.FileTest.EXISTS)) {
            const [ok, contents] = GLib.file_get_contents(configFile);
            if (ok) {
                const decoder = new TextDecoder('utf-8');
                return JSON.parse(decoder.decode(contents));
            }
        }
    } catch (e) {
        console.warn(`[Antigravity-vU] Could not load prefs: ${e.message}`);
    }
    return { pinned_group: 'auto' };
}

function savePrefs(prefs) {
    try {
        const configDir = GLib.build_filenamev([GLib.get_user_config_dir(), 'antigravity-vu']);
        GLib.mkdir_with_parents(configDir, 0o755);
        const configFile = GLib.build_filenamev([configDir, 'prefs.json']);
        const file = Gio.File.new_for_path(configFile);
        const jsonStr = JSON.stringify(prefs, null, 2);
        file.replace_contents(
            jsonStr,
            null,
            false,
            Gio.FileCreateFlags.REPLACE_DESTINATION,
            null
        );
    } catch (e) {
        console.warn(`[Antigravity-vU] Could not save prefs: ${e.message}`);
    }
}

function resolveCollectorCmd(extensionPath, pinnedGroup) {
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
    if (pinnedGroup && pinnedGroup !== 'auto') {
        cmd.push('--pin-group', pinnedGroup);
    }

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
        this._autoPeekTimerId = 0;
        this._autoPeekActive = false;
        this._lastIsWorking = false;
        this._lastData = null;
        this._prefs = loadPrefs();
        this._isRefreshing = false;

        this.add_style_class_name('ag-panel-button');
        this.add_style_class_name('ag-unified-island-indicator');
        this.y_align = Clutter.ActorAlign.CENTER;
        this.y_expand = true;

        this._buildPill();
        this._buildMenuShell();

        // Connect hover on our pill
        this._pillBox.connect('notify::hover', () => this._onHoverChanged());

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
        this._pillBox.track_hover = true;
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

        // Hover & Auto-peek details container (Dynamic Island expanded mode)
        this._hoverDetails = createHBox('ag-island-hover-details', 6);
        this._hoverDetails.visible = false;
        this._hoverDetails.opacity = 0;
        this._hoverDetails.y_align = Clutter.ActorAlign.CENTER;
        this._hoverDetails.y_expand = true;

        const sep1 = new St.Label({
            text: '•',
            style_class: 'ag-hover-sep',
            y_align: Clutter.ActorAlign.CENTER,
        });
        this._hoverDetails.add_child(sep1);

        this._hoverCtxLabel = new St.Label({
            text: 'Ctx: --',
            style_class: 'ag-hover-text',
            y_align: Clutter.ActorAlign.CENTER,
        });
        this._hoverDetails.add_child(this._hoverCtxLabel);

        const sep2 = new St.Label({
            text: '•',
            style_class: 'ag-hover-sep',
            y_align: Clutter.ActorAlign.CENTER,
        });
        this._hoverDetails.add_child(sep2);

        this._hoverSwarmLabel = new St.Label({
            text: '⚡ 0 ag',
            style_class: 'ag-hover-swarm',
            y_align: Clutter.ActorAlign.CENTER,
        });
        this._hoverDetails.add_child(this._hoverSwarmLabel);

        this._pillBox.add_child(this._hoverDetails);
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

            // Hover on any part of the capsule expands the island
            this._centerBoxHoverId = this._centerBox.connect('notify::hover', () => {
                this._onHoverChanged();
            });
        }

        // Add class to dateMenu for seamless pill edge and divider
        this._dateMenu = Main.panel.statusArea.dateMenu || Main.panel._dateMenu;
        if (this._dateMenu) {
            this._dateMenu.add_style_class_name('ag-unified-island-date');
        }

        this._applyTheme();
    }

    _removeUnifiedIsland() {
        if (this._centerBox) {
            if (this._centerBoxHoverId) {
                this._centerBox.disconnect(this._centerBoxHoverId);
                this._centerBoxHoverId = 0;
            }
            this._centerBox.remove_style_class_name('ag-unified-island-capsule');
            this._centerBox.remove_style_class_name('ag-theme-dark');
            this._centerBox.remove_style_class_name('ag-theme-light');
            this._removeAllAccentClasses(this._centerBox);
        }

        if (this._dateMenu) {
            this._dateMenu.remove_style_class_name('ag-unified-island-date');
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
       Hover & Dynamic Island Morphing
       ========================================================================= */

    _onHoverChanged() {
        const isHovered = (this._centerBox && this._centerBox.hover) || this._pillBox.hover;
        if (isHovered) {
            if (this._autoPeekTimerId) {
                GLib.source_remove(this._autoPeekTimerId);
                this._autoPeekTimerId = 0;
            }
            this._hoverDetails.visible = true;
            this._hoverDetails.ease({
                opacity: 255,
                duration: 200,
                mode: Clutter.AnimationMode.EASE_OUT_QUAD,
            });
        } else {
            if (this._autoPeekActive) {
                return;
            }
            this._hoverDetails.ease({
                opacity: 0,
                duration: 180,
                mode: Clutter.AnimationMode.EASE_OUT_QUAD,
                onComplete: () => {
                    const stillHovered = (this._centerBox && this._centerBox.hover) || this._pillBox.hover;
                    if (!stillHovered && !this._autoPeekActive) {
                        this._hoverDetails.visible = false;
                    }
                },
            });
        }
    }

    _triggerAutoPeek(durationMs) {
        if (this._autoPeekTimerId) {
            GLib.source_remove(this._autoPeekTimerId);
            this._autoPeekTimerId = 0;
        }

        this._autoPeekActive = true;
        this._hoverDetails.visible = true;
        this._hoverDetails.ease({
            opacity: 255,
            duration: 250,
            mode: Clutter.AnimationMode.EASE_OUT_QUAD,
        });

        this._autoPeekTimerId = GLib.timeout_add(
            GLib.PRIORITY_DEFAULT,
            durationMs,
            () => {
                this._autoPeekTimerId = 0;
                this._autoPeekActive = false;
                const isHovered = (this._centerBox && this._centerBox.hover) || this._pillBox.hover;
                if (!isHovered) {
                    this._hoverDetails.ease({
                        opacity: 0,
                        duration: 250,
                        mode: Clutter.AnimationMode.EASE_OUT_QUAD,
                        onComplete: () => {
                            const stillHovered = (this._centerBox && this._centerBox.hover) || this._pillBox.hover;
                            if (!stillHovered && !this._autoPeekActive) {
                                this._hoverDetails.visible = false;
                            }
                        },
                    });
                }
                return GLib.SOURCE_REMOVE;
            }
        );
    }

    /* =========================================================================
       Data Fetching & Subprocess Communication
       ========================================================================= */

    _fetchData(isManualRefresh = false) {
        if (this._isRefreshing && !isManualRefresh) {
            return;
        }

        this._isRefreshing = true;
        const cmd = resolveCollectorCmd(this._extension.path, this._prefs.pinned_group);

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

        // Check if working transitioned from false to true -> Morphing Auto-Peek!
        if (!this._lastIsWorking && isWorking) {
            this._triggerAutoPeek(AUTO_PEEK_DURATION_MS);
        }
        this._lastIsWorking = isWorking;

        // Update dot status class
        this._statusDot.remove_style_class_name('ag-dot-working');
        this._statusDot.remove_style_class_name('ag-dot-healthy');
        this._statusDot.remove_style_class_name('ag-dot-warning');
        this._statusDot.remove_style_class_name('ag-dot-critical');

        let remainingPct = 100;
        let quotaLabelText = '⚡ --%';

        // Check pinned group vs primary_quota
        const pinned = this._prefs.pinned_group || 'auto';
        let targetGroup = null;

        if (pinned !== 'auto' && Array.isArray(data.quota_groups)) {
            targetGroup = data.quota_groups.find(g => g.id === pinned || g.name.toLowerCase().includes(pinned.toLowerCase()));
        }

        if (targetGroup && targetGroup.buckets && targetGroup.buckets.length > 0) {
            const b = targetGroup.buckets.reduce((lowest, curr) => {
                if (!lowest) return curr;
                const lowestPct = Number(lowest.remaining_pct ?? 100);
                const currPct = Number(curr.remaining_pct ?? 100);
                return currPct < lowestPct ? curr : lowest;
            }, targetGroup.buckets[0]);
            remainingPct = b.remaining_pct;
            const shortName = formatShortGroupName(targetGroup.pill_name || targetGroup.name, targetGroup.id);
            quotaLabelText = `${shortName} ${Math.round(remainingPct)}%`;
        } else if (data.primary_quota) {
            remainingPct = data.primary_quota.remaining_pct;
            const shortName = formatShortGroupName(data.primary_quota.pill_name || data.primary_quota.group, null);
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

        // Update hover details text
        const ctxFormatted = data.active_context?.context_formatted || '--';
        const activeAgCount = data.swarm?.active_count || 0;
        this._hoverCtxLabel.text = `Ctx: ${ctxFormatted}`;
        this._hoverSwarmLabel.text = `⚡ ${activeAgCount} ag`;
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
        const headerBox = createHBox('ag-header-box', 8);

        const titleBox = createHBox(null, 8);
        titleBox.x_expand = true;

        const titleLabel = new St.Label({
            text: 'Antigravity View Usage',
            style_class: 'ag-header-title',
            y_align: Clutter.ActorAlign.CENTER,
        });
        titleBox.add_child(titleLabel);

        const tierBadge = new St.Label({
            text: data.user?.tier || 'Pro',
            style_class: 'ag-tier-badge',
            y_align: Clutter.ActorAlign.CENTER,
        });
        titleBox.add_child(tierBadge);

        const onlineBadge = new St.Label({
            text: data.user?.ls_online ? '● Online' : '● Offline',
            style_class: data.user?.ls_online ? 'ag-online-badge' : 'ag-offline-badge',
            y_align: Clutter.ActorAlign.CENTER,
        });
        titleBox.add_child(onlineBadge);

        headerBox.add_child(titleBox);

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
        headerBox.add_child(refreshBtn);

        this._contentBox.add_child(headerBox);

        // ================= 2. QUOTAS SECTION =================
        const quotaTitle = new St.Label({
            text: '📊 Quotas & Limites dos Modelos',
            style_class: 'ag-section-title',
        });
        this._contentBox.add_child(quotaTitle);

        if (Array.isArray(data.quota_groups)) {
            const currentPinned = this._prefs.pinned_group || 'auto';

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

                const isPinned = currentPinned === group.id;
                const pinBtn = new St.Button({
                    label: isPinned ? '📌 Fixado' : '📌 Fixar',
                    style_class: isPinned ? 'ag-pin-btn ag-pin-btn-active' : 'ag-pin-btn',
                    can_focus: true,
                });

                pinBtn.connect('clicked', () => {
                    if (isPinned) {
                        this._prefs.pinned_group = 'auto';
                    } else {
                        this._prefs.pinned_group = group.id;
                    }
                    savePrefs(this._prefs);
                    this._updatePill(this._lastData);
                    this._renderMenuContent();
                });

                groupHeader.add_child(pinBtn);
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

                        // Visual progress bar
                        const track = createHBox('ag-bar-track');

                        const fillWidth = Math.max(6, Math.round((pct / 100) * 360));
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

                this._contentBox.add_child(groupCard);
            }
        }

        // ================= 3. CONTEXT & SWARM =================
        const contextTitle = new St.Label({
            text: '⚡ Sessão Ativa & Swarm',
            style_class: 'ag-section-title',
        });
        this._contentBox.add_child(contextTitle);

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
        this._contentBox.add_child(contextCard);

        // Swarm Agents List
        const swarmActive = data.swarm?.active_count || 0;
        const swarmTotal = data.swarm?.total_alive || 0;
        const swarmHeading = new St.Label({
            text: `Agentes do Swarm (${swarmActive} ativos / ${swarmTotal} total):`,
            style_class: 'ag-section-title',
        });
        this._contentBox.add_child(swarmHeading);

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

            // Compact scroll if swarm has more than 4 agents
            if (data.swarm.agents.length > 4) {
                const agentsScroll = new St.ScrollView({
                    style_class: 'ag-agents-scroll',
                    overlay_scrollbars: true,
                    style: 'max-height: 135px;',
                    x_expand: true,
                });
                agentsScroll.set_child(agentsContainer);
                this._contentBox.add_child(agentsScroll);
            } else {
                this._contentBox.add_child(agentsContainer);
            }
        } else {
            const noAgentsLabel = new St.Label({
                text: 'Nenhum subagente ativo no momento.',
                style_class: 'ag-session-title',
            });
            this._contentBox.add_child(noAgentsLabel);
        }

        // ================= 4. MONTHLY TOKENS & TOP PROJECTS =================
        const monthTitle = new St.Label({
            text: `📈 Consumo no Mês (${data.monthly_tokens?.month || '--'}) • Total: ${data.monthly_tokens?.total_formatted || '0'}`,
            style_class: 'ag-section-title',
        });
        this._contentBox.add_child(monthTitle);

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

        this._contentBox.add_child(tokenCardsBox);

        // Top Projects (show top 3)
        if (Array.isArray(data.projects) && data.projects.length > 0) {
            const projHeading = new St.Label({
                text: 'Top Projetos:',
                style_class: 'ag-section-title',
            });
            this._contentBox.add_child(projHeading);

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

                this._contentBox.add_child(pBox);
            }
        }

        // ================= 5. FOOTER =================
        const now = new Date();
        const timeStr = now.toLocaleTimeString();
        const footerLabel = new St.Label({
            text: `Última atualização: ${timeStr} • Antigravity vU Linux v1.1.2`,
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

        if (this._autoPeekTimerId) {
            GLib.source_remove(this._autoPeekTimerId);
            this._autoPeekTimerId = 0;
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
