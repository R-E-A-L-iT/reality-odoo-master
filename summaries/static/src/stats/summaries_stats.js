/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { loadBundle } from "@web/core/assets";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, onWillUnmount, useEffect, useRef, useState } from "@odoo/owl";

const PERIODS = [4, 12, 26];
const COLORS = ["#714B67", "#00A09D", "#F0AD4E", "#5CB85C", "#D9534F"];

export class SummariesStats extends Component {
    static template = "summaries.SummariesStats";
    static props = {
        ...standardWidgetProps,
        record: { type: Object, optional: true },
        resId: { type: [Number, Boolean], optional: true },
    };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.containerRef = useRef("charts");
        this.state = useState({ loading: true, error: false, data: null, weeks: 12 });
        this._charts = [];

        onWillStart(async () => {
            await loadBundle("web.chartjs_lib");
            await this.loadStats();
        });

        useEffect(
            () => {
                this.renderCharts();
            },
            () => [this.state.data]
        );

        onWillUnmount(() => this.destroyCharts());
    }

    get resId() {
        return this.props.resId || (this.props.record && this.props.record.resId);
    }

    get periods() {
        return PERIODS;
    }

    get hasCharts() {
        return Boolean(this.state.data && this.state.data.charts.length);
    }

    async loadStats() {
        this.state.loading = true;
        this.state.error = false;
        try {
            if (!this.resId) {
                this.state.data = null;
                return;
            }
            this.state.data = await this.orm.call(
                "summaries.summary",
                "get_performance_stats",
                [[this.resId]],
                { weeks: this.state.weeks }
            );
        } catch (error) {
            this.state.error =
                (error && error.data && error.data.message) || (error && error.message) || String(error);
        } finally {
            this.state.loading = false;
        }
    }

    async setPeriod(weeks) {
        this.state.weeks = weeks;
        await this.loadStats();
    }

    destroyCharts() {
        for (const chart of this._charts) {
            try {
                chart.destroy();
            } catch (_error) {
                // a destroyed canvas is fine
            }
        }
        this._charts = [];
    }

    renderCharts() {
        this.destroyCharts();
        const data = this.state.data;
        const container = this.containerRef.el;
        if (!data || !container || !window.Chart) {
            return;
        }
        for (const canvas of container.querySelectorAll("canvas[data-key]")) {
            const chart = data.charts.find((candidate) => candidate.key === canvas.dataset.key);
            if (!chart) {
                continue;
            }
            this._charts.push(new window.Chart(canvas.getContext("2d"), this.chartConfig(chart, data)));
        }
    }

    chartConfig(chart, data) {
        return {
            type: chart.type === "line" ? "line" : "bar",
            data: {
                labels: data.labels,
                datasets: chart.datasets.map((dataset, index) => ({
                    label: dataset.label,
                    data: dataset.data,
                    backgroundColor: COLORS[index % COLORS.length],
                    borderColor: COLORS[index % COLORS.length],
                    borderWidth: 2,
                    fill: false,
                    tension: 0.3,
                })),
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { mode: "index", intersect: false },
                scales: { y: { beginAtZero: true } },
                onClick: (event, elements) => this.onChartClick(chart, data, elements),
            },
        };
    }

    onChartClick(chart, data, elements) {
        if (!elements || !elements.length || !chart.drilldown) {
            return;
        }
        const range = data.ranges[elements[0].index];
        if (!range) {
            return;
        }
        const { model, date_field: dateField, domain } = chart.drilldown;
        this.action.doAction({
            type: "ir.actions.act_window",
            name: chart.title,
            res_model: model,
            domain: [...domain, [dateField, ">=", range[0]], [dateField, "<", range[1]]],
            views: [
                [false, "list"],
                [false, "form"],
            ],
            target: "current",
        });
    }
}

export const summariesStats = { component: SummariesStats };

registry.category("view_widgets").add("summaries_stats", summariesStats);
