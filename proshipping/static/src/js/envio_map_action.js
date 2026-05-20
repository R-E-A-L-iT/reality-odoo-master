/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onMounted, onWillUnmount, useRef, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class EnvioMapAction extends Component {
    static template = "proshipping.EnvioMapAction";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.containerRef = useRef("mapContainer");
        this.state = useState({ loading: true, error: null, count: 0 });

        this._map = null;
        this._markersLayer = null;
        this._leafletLoaded = false;

        onMounted(async () => {
            try {
                await this._ensureLeaflet();
                await this._initMap();
                await this._loadMarkers();
            } catch (e) {
                console.error(e);
                this.state.error = (e && e.message) ? e.message : String(e);
            } finally {
                this.state.loading = false;
            }
        });

        onWillUnmount(() => {
            try {
                if (this._map) {
                    this._map.remove();
                    this._map = null;
                }
            } catch (_) {}
        });
    }

    async _ensureLeaflet() {
        if (window.L && window.L.map && window.L.markerClusterGroup) {
            this._leafletLoaded = true;
            return;
        }

        const loadLink = (href) => new Promise((resolve, reject) => {
            const link = document.createElement("link");
            link.rel = "stylesheet";
            link.href = href;
            link.onload = resolve;
            link.onerror = () => reject(new Error(`Failed to load CSS: ${href}`));
            document.head.appendChild(link);
        });

        const loadScript = (src) => new Promise((resolve, reject) => {
            const script = document.createElement("script");
            script.src = src;
            script.onload = resolve;
            script.onerror = () => reject(new Error(`Failed to load JS: ${src}`));
            document.head.appendChild(script);
        });

        await loadLink("https://unpkg.com/leaflet@1.9.4/dist/leaflet.css");
        await loadScript("https://unpkg.com/leaflet@1.9.4/dist/leaflet.js");
        await loadLink("https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.css");
        await loadLink("https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.Default.css");
        await loadScript("https://unpkg.com/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js");

        this._leafletLoaded = true;
    }

    _injectClusterStyles() {
        if (document.getElementById("ps-cluster-styles")) return;
        const style = document.createElement("style");
        style.id = "ps-cluster-styles";
        style.textContent = `
            .ps-cluster { background: transparent !important; border: none !important; }
            .ps-cluster-inner {
                width: 40px; height: 40px;
                background-color: rgba(26, 105, 133, 0.75);
                border: 3px solid rgba(26, 105, 133, 1);
                border-radius: 50%;
                color: #fff;
                font-weight: 700;
                font-size: 13px;
                display: flex;
                align-items: center;
                justify-content: center;
                box-sizing: border-box;
            }
        `;
        document.head.appendChild(style);
    }

    async _initMap() {
        const el = this.containerRef.el;
        if (!el) throw new Error("Map container not found");

        this._injectClusterStyles();

        this._map = window.L.map(el).setView([20, 0], 2);

        window.L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
            maxZoom: 19,
            attribution: "&copy; OpenStreetMap contributors",
        }).addTo(this._map);

        this._markersLayer = window.L.markerClusterGroup({
            iconCreateFunction: (cluster) => window.L.divIcon({
                html: `<div class="ps-cluster-inner">${cluster.getChildCount()}</div>`,
                className: "ps-cluster",
                iconSize: [40, 40],
            }),
        }).addTo(this._map);
    }

    async _loadMarkers() {
        const points = await this.orm.call("envio.package", "get_map_points", [], {});

        this.state.count = points.length;
        this._markersLayer.clearLayers();

        const bounds = [];

        for (const p of points) {
            const lat = Number(p.lat);
            const lng = Number(p.lng);
            if (!Number.isFinite(lat) || !Number.isFinite(lng)) continue;

            bounds.push([lat, lng]);

            const popup = `
                <div style="min-width:220px">
                    <div><strong>${this._escape(p.name || "")}</strong></div>
                    <div>Status: ${this._escape(p.status || "")}</div>
                    <div>Battery: ${Number.isFinite(Number(p.battery_percent)) ? `${p.battery_percent}%` : ""}</div>
                    <div>Last: ${this._escape(p.last_event_at || "")}</div>
                    <div style="margin-top:8px">
                        <a href="#" data-odoo-open="${p.id}">Open record</a>
                    </div>
                </div>
            `;

            const marker = window.L.marker([lat, lng]).addTo(this._markersLayer);
            marker.bindPopup(popup);

            marker.on("popupopen", (evt) => {
                const node = evt.popup.getElement();
                if (!node) return;
                const link = node.querySelector("[data-odoo-open]");
                if (!link) return;
                link.addEventListener("click", (e) => {
                    e.preventDefault();
                    const resId = Number(link.getAttribute("data-odoo-open"));
                    this.action.doAction({
                        type: "ir.actions.act_window",
                        res_model: "envio.package",
                        res_id: resId,
                        views: [[false, "form"]],
                        target: "current",
                    });
                });
            });
        }

        if (bounds.length) {
            this._map.fitBounds(bounds, { padding: [30, 30] });
        }
    }

    _escape(s) {
        return String(s)
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#039;");
    }
}

registry.category("actions").add("proshipping.envio_map_action", EnvioMapAction);
