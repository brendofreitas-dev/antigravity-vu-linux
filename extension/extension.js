/* extension.js
 * Antigravity View Usage Dynamic Island Extension for GNOME Shell 45-50
 *
 * Copyright (C) 2026 Brendo Freitas
 * SPDX-License-Identifier: MIT
 */

import Gio from 'gi://Gio';
import { Extension } from 'resource:///org/gnome/shell/extensions/extension.js';

export default class AntigravityExtension extends Extension {
    _getIslandModuleUrl() {
        const islandPath = `${this.path}/island.js`;
        try {
            const file = Gio.File.new_for_path(islandPath);
            const info = file.query_info(
                'time::modified,time::modified-usec,standard::size',
                Gio.FileQueryInfoFlags.NONE,
                null
            );
            const sec = info.get_attribute_uint64('time::modified');
            const usec = info.get_attribute_uint32('time::modified-usec');
            const size = info.get_attribute_uint64('standard::size');
            return `file://${islandPath}?v=${sec}_${usec}_${size}`;
        } catch (e) {
            return `file://${islandPath}`;
        }
    }

    async enable() {
        this._enabled = true;
        let islandModule = null;

        try {
            const moduleUrl = this._getIslandModuleUrl();
            islandModule = await import(moduleUrl);
        } catch (e) {
            console.warn(`[Antigravity-vU] Deterministic cache import failed: ${e.message}, attempting static import fallback...`);
            try {
                islandModule = await import('./island.js');
            } catch (fallbackErr) {
                console.error(`[Antigravity-vU] Static import fallback failed: ${fallbackErr.message}`, fallbackErr);
                throw fallbackErr;
            }
        }

        // Abort if extension was disabled while awaiting the import
        if (!this._enabled) {
            if (islandModule?.disableIsland) {
                try {
                    islandModule.disableIsland();
                } catch (err) {}
            }
            return;
        }

        this._disableIsland = islandModule.disableIsland;
        this._indicator = await islandModule.initIsland(this);
    }

    disable() {
        this._enabled = false;

        if (this._disableIsland) {
            try {
                this._disableIsland();
            } catch (e) {
                console.warn(`[Antigravity-vU] Error in disableIsland: ${e.message}`);
            }
            this._disableIsland = null;
            this._indicator = null;
        } else if (this._indicator) {
            try {
                this._indicator.destroy();
            } catch (e) {
                console.warn(`[Antigravity-vU] Error destroying indicator: ${e.message}`);
            }
            this._indicator = null;
        }
    }
}
