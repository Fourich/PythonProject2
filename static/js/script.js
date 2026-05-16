const canvas = document.getElementById('moneyChart');
let selectedHistoryItem = null;
let showAllHistory = false;
let currentChartMode = startViewInterval;
let currentChartType = 'growth';

function getCurrentRows(mode) {
    if (selectedHistoryItem) {
        return mode === 'months' ? selectedHistoryItem.months_data : selectedHistoryItem.years_data;
    }

    if (mode === 'months') {
        return months.map((month, index) => ({
            month: month,
            year: Math.floor((month - 1) / 12) + 1,
            balance: monthBalances[index],
            payments: monthPayments[index],
            profit: monthProfits[index],
            real_sum: monthRealSums[index],
            inflation_loss: monthBalances[index] - monthRealSums[index]
        }));
    }

    return years.map((year, index) => ({
        year: year,
        balance: balances[index],
        payments: payments[index],
        profit: profits[index],
        real_sum: realSums[index],
        inflation_loss: balances[index] - realSums[index]
    }));
}

function dataFromRows(rows, mode) {
    return {
        labels: rows.map(row => mode === 'months' ? row.month + ' мес.' : row.year + ' год'),
        balances: rows.map(row => row.balance),
        payments: rows.map(row => row.payments),
        profits: rows.map(row => row.profit),
        realSums: rows.map(row => row.real_sum),
        inflationLosses: rows.map(row => row.inflation_loss || 0),
        profitability: rows.map(row => row.payments ? Number((row.profit / row.payments * 100).toFixed(2)) : 0)
    };
}

function makeChartData(mode) {
    return dataFromRows(getCurrentRows(mode), mode);
}

function makeGrowthDatasets(data) {
    return [
        {
            label: 'Итоговая сумма',
            data: data.balances,
            borderColor: '#16a34a',
            backgroundColor: 'rgba(22, 163, 74, 0.12)',
            fill: true,
            tension: 0.35
        },
        {
            label: 'Внесено денег',
            data: data.payments,
            borderColor: '#3b82f6',
            backgroundColor: 'rgba(59, 130, 246, 0.08)',
            fill: true,
            tension: 0.35
        },
        {
            label: 'Доход',
            data: data.profits,
            borderColor: '#f59e0b',
            backgroundColor: 'rgba(245, 158, 11, 0.08)',
            fill: true,
            tension: 0.35
        },
        {
            label: 'С учётом инфляции',
            data: data.realSums,
            borderColor: '#ef4444',
            backgroundColor: 'rgba(239, 68, 68, 0.06)',
            fill: true,
            tension: 0.35
        }
    ];
}

function makeStructureDatasets(data) {
    return [
        {
            type: 'bar',
            label: 'Внесено денег',
            data: data.payments,
            backgroundColor: 'rgba(59, 130, 246, 0.75)',
            stack: 'money'
        },
        {
            type: 'bar',
            label: 'Доход',
            data: data.profits,
            backgroundColor: 'rgba(22, 163, 74, 0.75)',
            stack: 'money'
        }
    ];
}

function makeProfitDatasets(data) {
    return [
        {
            label: 'Доходность, % от внесённых средств',
            data: data.profitability,
            borderColor: '#8b5cf6',
            backgroundColor: 'rgba(139, 92, 246, 0.12)',
            fill: true,
            tension: 0.35
        }
    ];
}

function makeInflationDatasets(data) {
    return [
        {
            label: 'Номинальная сумма',
            data: data.balances,
            borderColor: '#16a34a',
            backgroundColor: 'rgba(22, 163, 74, 0.08)',
            fill: true,
            tension: 0.35
        },
        {
            label: 'Реальная сумма',
            data: data.realSums,
            borderColor: '#ef4444',
            backgroundColor: 'rgba(239, 68, 68, 0.08)',
            fill: true,
            tension: 0.35
        },
        {
            label: 'Потери от инфляции',
            data: data.inflationLosses,
            borderColor: '#f97316',
            backgroundColor: 'rgba(249, 115, 22, 0.1)',
            fill: true,
            tension: 0.35
        }
    ];
}

function makeDatasets(data) {
    if (currentChartType === 'structure') {
        return makeStructureDatasets(data);
    }
    if (currentChartType === 'profit') {
        return makeProfitDatasets(data);
    }
    if (currentChartType === 'inflation') {
        return makeInflationDatasets(data);
    }
    return makeGrowthDatasets(data);
}

function makeHistoryDatasets(mode) {
    return historyData.map((item, index) => {
        const rows = mode === 'months' ? item.months_data : item.years_data;
        const colors = ['#16a34a', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6', '#14b8a6', '#f97316', '#64748b'];
        let data = rows.map(row => row.balance);
        let labelPrefix = 'Итог';

        if (currentChartType === 'profit') {
            data = rows.map(row => row.payments ? Number((row.profit / row.payments * 100).toFixed(2)) : 0);
            labelPrefix = 'Доходность';
        }
        if (currentChartType === 'inflation') {
            data = rows.map(row => row.real_sum);
            labelPrefix = 'С учётом инфляции';
        }
        if (currentChartType === 'structure') {
            data = rows.map(row => row.profit);
            labelPrefix = 'Доход';
        }

        return {
            label: labelPrefix + ': ' + item.type_name + ' — ' + Number(item.final_sum).toLocaleString('ru-RU') + ' ₽',
            data: data,
            borderColor: colors[index % colors.length],
            backgroundColor: 'transparent',
            fill: false,
            tension: 0.25
        };
    });
}

function updateChartScale() {
    if (currentChartType === 'profit') {
        moneyChart.options.scales.y.ticks.callback = function(value) {
            return value.toLocaleString('ru-RU') + ' %';
        };
    } else {
        moneyChart.options.scales.y.ticks.callback = function(value) {
            return value.toLocaleString('ru-RU') + ' ₽';
        };
    }
}

function updateChart() {
    if (showAllHistory && historyData.length) {
        const maxLength = Math.max(...historyData.map(item => {
            const rows = currentChartMode === 'months' ? item.months_data : item.years_data;
            return rows.length;
        }));

        moneyChart.data.labels = Array.from({ length: maxLength }, (_, index) => {
            return currentChartMode === 'months' ? (index + 1) + ' мес.' : (index + 1) + ' год';
        });
        moneyChart.data.datasets = makeHistoryDatasets(currentChartMode);
    } else {
        const data = makeChartData(currentChartMode);
        moneyChart.data.labels = data.labels;
        moneyChart.data.datasets = makeDatasets(data);
    }

    updateChartScale();
    moneyChart.update();
}

const startChartData = makeChartData(currentChartMode);

const moneyChart = new Chart(canvas, {
    type: 'line',
    data: {
        labels: startChartData.labels,
        datasets: makeDatasets(startChartData)
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                position: 'bottom'
            }
        },
        scales: {
            x: {
                stacked: false
            },
            y: {
                stacked: false,
                beginAtZero: true,
                ticks: {
                    callback: function(value) {
                        return value.toLocaleString('ru-RU') + ' ₽';
                    }
                }
            }
        }
    }
});

const chartTabs = document.querySelectorAll('.chart-tab');
chartTabs.forEach(tab => {
    tab.addEventListener('click', () => {
        chartTabs.forEach(item => item.classList.remove('active'));
        tab.classList.add('active');
        currentChartMode = tab.dataset.chart;
        updateChart();
    });
});

const chartTypeTabs = document.querySelectorAll('.chart-type-tab');
chartTypeTabs.forEach(tab => {
    tab.addEventListener('click', () => {
        chartTypeTabs.forEach(item => item.classList.remove('active'));
        tab.classList.add('active');
        currentChartType = tab.dataset.chartType;
        moneyChart.options.scales.x.stacked = currentChartType === 'structure';
        moneyChart.options.scales.y.stacked = currentChartType === 'structure';
        updateChart();
    });
});

const historyItems = document.querySelectorAll('.history-item');
const historyAllButton = document.querySelector('.history-all-button');

historyItems.forEach(button => {
    button.addEventListener('click', () => {
        historyItems.forEach(item => item.classList.remove('active'));
        button.classList.add('active');
        if (historyAllButton) {
            historyAllButton.classList.remove('active');
        }

        showAllHistory = false;
        selectedHistoryItem = historyData.find(item => item.id === Number(button.dataset.historyId));
        updateChart();
    });
});

if (historyAllButton) {
    historyAllButton.addEventListener('click', () => {
        historyItems.forEach(item => item.classList.remove('active'));
        historyAllButton.classList.add('active');
        selectedHistoryItem = null;
        showAllHistory = true;
        moneyChart.options.scales.x.stacked = false;
        moneyChart.options.scales.y.stacked = false;
        updateChart();
    });
}

const modeInputs = document.querySelectorAll('input[name="calc_type"]');
const form = document.querySelector('form');

function updateFields() {
    const mode = document.querySelector('input[name="calc_type"]:checked').value;

    document.querySelector('.goal-field').style.display = mode === 'income' ? 'none' : 'block';
    document.querySelector('.start-sum-field').style.display = mode === 'start_sum' ? 'none' : 'block';
    document.querySelector('.period-field').style.display = mode === 'period' ? 'none' : 'grid';
    document.querySelector('.rate-field').style.display = mode === 'rate' ? 'none' : 'block';
    document.querySelectorAll('.payment-field').forEach(item => {
        item.style.display = mode === 'payment' ? 'none' : '';
    });
}

function updateOptionalFields() {
    const reinvestCheckbox = document.querySelector('input[name="reinvest"]');
    const taxCheckbox = document.querySelector('input[name="tax_enabled"]');
    const inflationCheckbox = document.querySelector('input[name="inflation_enabled"]');

    document.querySelector('.reinvest-field').style.display = reinvestCheckbox.checked ? 'block' : 'none';
    document.querySelector('.tax-field').style.display = taxCheckbox.checked ? 'block' : 'none';
    document.querySelector('.inflation-field').style.display = inflationCheckbox.checked ? 'block' : 'none';
}

modeInputs.forEach(input => {
    input.addEventListener('change', updateFields);
});

document.querySelector('input[name="reinvest"]').addEventListener('change', updateOptionalFields);
document.querySelector('input[name="tax_enabled"]').addEventListener('change', updateOptionalFields);
document.querySelector('input[name="inflation_enabled"]').addEventListener('change', updateOptionalFields);

updateFields();
updateOptionalFields();

const presetButtons = document.querySelectorAll('.presets button');
presetButtons.forEach(button => {
    button.addEventListener('click', () => {
        const input = form.querySelector(`[name="${button.dataset.name}"]`);
        input.value = button.dataset.value;
    });
});

const tableTabs = document.querySelectorAll('.table-tab');
const tableViews = document.querySelectorAll('.table-view');

tableTabs.forEach(tab => {
    tab.addEventListener('click', () => {
        tableTabs.forEach(item => item.classList.remove('active'));
        tableViews.forEach(item => item.classList.remove('active'));

        tab.classList.add('active');
        document.getElementById(tab.dataset.table).classList.add('active');
    });
});
