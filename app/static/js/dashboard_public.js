document.addEventListener('DOMContentLoaded', function() {
    const elements = {
        applyBtn: document.getElementById('dashboardApplyBtn'),
        resetBtn: document.getElementById('dashboardResetBtn'),
        filterError: document.getElementById('dashboardFilterError'),
        updatedAt: document.getElementById('dashboardUpdatedAt'),
        deptFilter: document.getElementById('dashboardDeptFilter'),
        statusFilter: document.getElementById('dashboardStatusFilter'),
        fromMonth: document.getElementById('dashboardFromMonth'),
        toMonth: document.getElementById('dashboardToMonth'),
        metricTotal: document.getElementById('metricTotal'),
        metricPending: document.getElementById('metricPending'),
        metricInProgress: document.getElementById('metricInProgress'),
        metricResolved: document.getElementById('metricResolved'),
        metricHighPriority: document.getElementById('metricHighPriority'),
        metricSlaCompliance: document.getElementById('metricSlaCompliance'),
        activeDepartments: document.getElementById('activeDepartmentsPill'),
        delayedInsight: document.getElementById('insightDelayedValue'),
        reopenedInsight: document.getElementById('insightReopenedValue'),
        backlogInsight: document.getElementById('insightBacklogValue'),
        deptScoreboard: document.getElementById('deptScoreboardGrid'),
        bestDepartmentName: document.getElementById('bestDepartmentName'),
        bestDepartmentScore: document.getElementById('bestDepartmentScore'),
        worstDepartmentName: document.getElementById('worstDepartmentName'),
        worstDepartmentScore: document.getElementById('worstDepartmentScore'),
        recentActivityBody: document.getElementById('recentActivityBody'),
        monthlyState: document.getElementById('monthlyChartState'),
        statusState: document.getElementById('statusChartState'),
        deptState: document.getElementById('deptChartState'),
        resolutionState: document.getElementById('resolutionTimeChartState'),
        slaState: document.getElementById('slaComplianceChartState')
    };

    const charts = {
        monthly: null,
        status: null,
        dept: null,
        resolution: null,
        sla: null
    };

    const chartConfigs = {
        monthly: {
            elementId: 'monthlyChart',
            stateId: 'monthlyChartState',
            makeData: (payload) => ({
                labels: payload.labels || [],
                datasets: [{
                    label: 'Complaints',
                    data: payload.data || [],
                    borderColor: '#1a56db',
                    backgroundColor: 'rgba(26, 86, 219, 0.12)',
                    fill: true,
                    tension: 0.3
                }]
            }),
            type: 'line'
        },
        status: {
            elementId: 'statusChart',
            stateId: 'statusChartState',
            makeData: (payload) => ({
                labels: payload.labels || [],
                datasets: [{
                    data: payload.data || [],
                    backgroundColor: [
                        '#f59e0b',
                        '#06b6d4',
                        '#1a56db',
                        '#ef4444',
                        '#64748b',
                        '#10b981'
                    ]
                }]
            }),
            type: 'doughnut'
        },
        dept: {
            elementId: 'deptChart',
            stateId: 'deptChartState',
            makeData: (payload) => ({
                labels: payload.labels || [],
                datasets: [{
                    label: 'Complaint Count',
                    data: payload.data || [],
                    backgroundColor: '#1a56db',
                    borderWidth: 0
                }]
            }),
            type: 'bar'
        },
        resolution: {
            elementId: 'resolutionTimeChart',
            stateId: 'resolutionTimeChartState',
            makeData: (payload) => ({
                labels: payload.labels || [],
                datasets: [{
                    label: 'Avg Resolution (hrs)',
                    data: payload.data || [],
                    borderColor: '#0ea5e9',
                    backgroundColor: 'rgba(14, 165, 233, 0.15)',
                    fill: true,
                    tension: 0.3
                }]
            }),
            type: 'line'
        },
        sla: {
            elementId: 'slaComplianceChart',
            stateId: 'slaComplianceChartState',
            makeData: (payload) => ({
                labels: payload.labels || [],
                datasets: [{
                    label: 'SLA Compliance %',
                    data: payload.data || [],
                    borderColor: '#16a34a',
                    backgroundColor: 'rgba(22, 163, 74, 0.12)',
                    fill: true,
                    tension: 0.25
                }]
            }),
            type: 'line'
        }
    };

    const commonOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: true, position: 'bottom' } }
    };

    function safeTextContent(node, value) {
        if (node) {
            node.textContent = value;
        }
    }

    function setFilterError(message, isError = true) {
        if (!elements.filterError) {
            return;
        }

        if (message) {
            elements.filterError.textContent = message;
            elements.filterError.classList.toggle('d-none', !isError);
            return;
        }

        elements.filterError.classList.add('d-none');
        elements.filterError.textContent = '';
    }

    function setChartState(stateId, loading = true, message = '') {
        const stateEl = document.getElementById(stateId);
        if (!stateEl) {
            return;
        }

        if (loading) {
            stateEl.classList.remove('d-none');
            stateEl.innerHTML = `<i class="fas fa-spinner fa-spin me-2"></i>${message || 'Loading...'}`;
            return;
        }

        stateEl.classList.add('d-none');
    }

    function destroyChart(chartRef) {
        if (chartRef && typeof chartRef.destroy === 'function') {
            chartRef.destroy();
        }
    }

    function normalizePayload(payload) {
        const safe = payload || {};
        return {
            stats: safe.stats || {},
            active_departments: Number(safe.active_departments || 0),
            best_department: safe.best_department || null,
            worst_department: safe.worst_department || null,
            dept_stats: safe.dept_stats || [],
            recent_complaints: safe.recent_complaints || []
        };
    }

    function applyOverviewPayload(payload) {
        const data = normalizePayload(payload);
        const stats = data.stats || {};

        safeTextContent(elements.metricTotal, stats.total || 0);
        safeTextContent(elements.metricPending, stats.pending || 0);
        safeTextContent(elements.metricInProgress, (stats.pending || 0) + (stats.under_review || 0) + (stats.action_taken || 0) + (stats.reopened || 0));
        safeTextContent(elements.metricResolved, stats.closed || 0);
        safeTextContent(elements.metricHighPriority, stats.high_priority || 0);
        safeTextContent(elements.metricSlaCompliance, `${Number(stats.sla_compliance || 0).toFixed(2)}`);
        safeTextContent(elements.activeDepartments, `${data.active_departments || 0} active departments`);

        safeTextContent(elements.delayedInsight, `${stats.delayed || 0} delayed complaints`);
        safeTextContent(elements.reopenedInsight, `${stats.reopened || 0} reopened complaints`);
        safeTextContent(elements.backlogInsight, `${Number(stats.pending || 0) > 0 ? 'Pending complaints in backlog.' : 'No pending backlog.'}`);

        if (data.best_department) {
            safeTextContent(elements.bestDepartmentName, data.best_department.name || 'N/A');
            safeTextContent(elements.bestDepartmentScore, `${data.best_department.score || 'N/A'}`);
        } else {
            safeTextContent(elements.bestDepartmentName, 'N/A');
            safeTextContent(elements.bestDepartmentScore, 'N/A');
        }

        if (data.worst_department) {
            safeTextContent(elements.worstDepartmentName, data.worst_department.name || 'N/A');
            safeTextContent(elements.worstDepartmentScore, `${data.worst_department.score || 'N/A'}`);
        } else {
            safeTextContent(elements.worstDepartmentName, 'N/A');
            safeTextContent(elements.worstDepartmentScore, 'N/A');
        }

        if (elements.recentActivityBody) {
            if (!data.recent_complaints.length) {
                elements.recentActivityBody.innerHTML = '<tr><td colspan="5" class="text-center text-muted py-4">No recent activity for selected filters.</td></tr>';
            } else {
                elements.recentActivityBody.innerHTML = data.recent_complaints
                    .map((item) => `<tr>
                        <td data-label="Tracking ID"><code>${item.tracking_id || '-'}</code></td>
                        <td data-label="Department">${item.department || '-'}</td>
                        <td data-label="Service" class="d-none d-md-table-cell">${item.service || '-'}</td>
                        <td data-label="Status"><span class="badge bg-${item.status_badge || 'secondary'}">${item.status || '-'}</span></td>
                        <td data-label="Submitted">${item.submitted_at || '-'}</td>
                    </tr>`)
                    .join('');
            }
        }

        if (elements.updatedAt) {
            const now = new Date();
            elements.updatedAt.textContent = `Last updated: ${now.toLocaleDateString()} ${now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
        }

        renderDepartmentScoreboard(data.dept_stats || []);
    }

    function renderDepartmentScoreboard(departments) {
        if (!elements.deptScoreboard) {
            return;
        }

        if (!departments || !departments.length) {
            elements.deptScoreboard.innerHTML = '<div class="col-12"><div class="text-muted">No department data available for current filters.</div></div>';
            return;
        }

        elements.deptScoreboard.innerHTML = departments
            .map((dept, index) => `
                <div class="col-md-6 col-xl-4">
                    <div class="dept-rank-card h-100">
                        <div class="dept-rank-head mb-3">
                            <div>
                                <h6 class="fw-semibold mb-1">${dept.name || 'Department'}</h6>
                                <p class="small text-muted mb-0">${dept.total || 0} total complaints</p>
                            </div>
                            <span class="dept-rank-badge">#${index + 1}</span>
                        </div>
                        <div class="row g-2 text-center mb-3">
                            <div class="col-4"><div class="dept-rank-stat"><div class="fw-bold">${dept.pending || 0}</div><small class="text-muted">Pending</small></div></div>
                            <div class="col-4"><div class="dept-rank-stat dept-rank-stat-success"><div class="fw-bold text-success">${dept.closed || 0}</div><small class="text-muted">Closed</small></div></div>
                            <div class="col-4"><div class="dept-rank-stat dept-rank-stat-danger"><div class="fw-bold text-danger">${dept.delayed || 0}</div><small class="text-muted">Delayed</small></div></div>
                        </div>
                        <div class="d-flex justify-content-between small mb-1"><span>Resolution Rate</span><span class="fw-semibold">${dept.resolution_rate || 0}%</span></div>
                        <div class="progress" style="height: 6px;"><div class="progress-bar bg-success" style="width: ${dept.resolution_rate || 0}%"></div></div>
                        <div class="d-flex justify-content-between small mt-2"><span class="text-muted">Delay penalty ${dept.delay_penalty || 0}%</span><span class="fw-semibold">Score ${dept.score || 0}</span></div>
                    </div>
                </div>
            `).join('');
    }

    function parseFilterParams() {
        const params = new URLSearchParams();

        if (elements.deptFilter && elements.deptFilter.value) {
            params.set('department_id', elements.deptFilter.value);
        }
        if (elements.statusFilter && elements.statusFilter.value) {
            params.set('status', elements.statusFilter.value);
        }
        if (elements.fromMonth && elements.fromMonth.value) {
            params.set('from_month', elements.fromMonth.value);
        }
        if (elements.toMonth && elements.toMonth.value) {
            params.set('to_month', elements.toMonth.value);
        }

        return params;
    }

    function buildEndpointUrl(endpoint) {
        const params = parseFilterParams();
        const query = params.toString();
        return query ? `${endpoint}?${query}` : endpoint;
    }

    async function loadChart(config) {
        const chartConfig = chartConfigs[config];
        if (!chartConfig) {
            return;
        }

        const canvasId = chartConfig.elementId;
        const stateId = chartConfig.stateId;
        const canvas = document.getElementById(canvasId);
        if (!canvas || typeof Chart === 'undefined') {
            return;
        }

        setChartState(stateId, true, 'Loading');

        const endpoints = {
            monthly: '/api/chart/monthly',
            status: '/api/chart/status',
            dept: '/api/chart/dept',
            resolution: '/api/chart/resolution-time',
            sla: '/api/chart/sla-compliance'
        };

        try {
            const response = await fetch(buildEndpointUrl(endpoints[config]));
            if (!response.ok) {
                throw new Error(`Chart request failed (${response.status})`);
            }
            const payload = await response.json();
            const chartData = chartConfig.makeData(payload);

            destroyChart(charts[config]);
            const common = { ...commonOptions };
            if (chartConfig.type === 'doughnut') {
                common.maintainAspectRatio = false;
            }

            charts[config] = new Chart(canvas, {
                type: chartConfig.type,
                data: chartData,
                options: common
            });

            setChartState(stateId, false);
        } catch (error) {
            console.error('Chart load failed:', error);
            setChartState(stateId, false);
            const stateEl = document.getElementById(stateId);
            if (stateEl) {
                stateEl.classList.remove('d-none');
                stateEl.innerHTML = '<i class="fas fa-exclamation-circle me-2"></i>Unable to load chart';
            }
        }
    }

    async function loadOverviewAndCharts() {
        if (!elements.applyBtn) {
            return;
        }

        setFilterError('');
        elements.applyBtn.disabled = true;
        elements.applyBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Applying';

        try {
            const overviewResponse = await fetch(buildEndpointUrl('/api/dashboard/overview'));
            if (!overviewResponse.ok) {
                throw new Error(`Overview request failed (${overviewResponse.status})`);
            }
            const payload = await overviewResponse.json();
            applyOverviewPayload(payload);

            await Promise.all([
                loadChart('monthly'),
                loadChart('status'),
                loadChart('dept'),
                loadChart('resolution'),
                loadChart('sla')
            ]);
        } catch (error) {
            console.error(error);
            setFilterError('Unable to load dashboard data. Please retry.');
        } finally {
            elements.applyBtn.disabled = false;
            elements.applyBtn.innerHTML = '<i class="fas fa-filter me-1"></i>Apply';
        }
    }

    function resetFilters() {
        if (elements.deptFilter) {
            elements.deptFilter.value = '';
        }
        if (elements.statusFilter) {
            elements.statusFilter.value = '';
        }
        if (elements.fromMonth) {
            elements.fromMonth.value = '';
        }
        if (elements.toMonth) {
            elements.toMonth.value = '';
        }
        loadOverviewAndCharts();
    }

    elements.applyBtn?.addEventListener('click', loadOverviewAndCharts);
    elements.resetBtn?.addEventListener('click', resetFilters);

    if (elements.applyBtn) {
        elements.applyBtn.click();
    } else {
        loadOverviewAndCharts();
    }
});
