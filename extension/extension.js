/* extension.js
 * Antigravity View Usage Dynamic Island Extension for GNOME Shell 45-50
 *
 * Copyright (C) 2026 Brendo Freitas
 * SPDX-License-Identifier: MIT
 */

import { Extension } from 'resource:///org/gnome/shell/extensions/extension.js';

export default class AntigravityExtension extends Extension {
    async enable() {
        try {
            // Dynamic import with file:// URI scheme and timestamp query parameter busts the GJS module cache,
            // allowing true hot-reloading of code changes without logging out of the Wayland session!
            const moduleUrl = `file://${this.path}/island.js?t=${Date.now()}`;
            const { initIsland, disableIsland } = await import(moduleUrl);
            this._disableIsland = disableIsland;
            this._indicator = await initIsland(this);
        } catch (e) {
            console.warn(`[Antigravity-vU] Dynamic cache-busting import failed: ${e.message}, attempting static import...`);
            try {
                const { initIsland, disableIsland } = await import('./island.js');
                this._disableIsland = disableIsland;
                this._indicator = await initIsland(this);
            } catch (fallbackErr) {
                console.error(`[Antigravity-vU] Static import fallback failed: ${fallbackErr.message}`, fallbackErr);
            }
        }
    }

    disable() {
        if (this._disableIsland) {
            try {
                this._disableIsland();
            } catch (e) {
                console.warn(`[Antigravity-vU] Error in disableIsland: ${e.message}`);
            }
            this._disableIsland = null;
        }

        if (this._indicator) {
            try {
                this._indicator.destroy();
            } catch (e) {
                console.warn(`[Antigravity-vU] Error destroying indicator: ${e.message}`);
            }
            this._indicator = null;
        }
    }
}
