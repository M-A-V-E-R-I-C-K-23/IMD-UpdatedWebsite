
document.addEventListener('DOMContentLoaded', function () {
    const selectedStation = window.SELECTED_STATION;
    const refreshBtn = document.getElementById('refreshBtn');

    const colors = [
        'rgb(0, 123, 255)',
        'rgb(40, 167, 69)',
        'rgb(255, 193, 7)'
    ];

    const incompleteColors = [
        'rgba(0, 123, 255, 0.4)',
        'rgba(40, 167, 69, 0.4)',
        'rgba(255, 193, 7, 0.4)'
    ];

    function fetchData() {
        fetch(`/api/data?station=${selectedStation}`)
            .then(response => response.json())
            .then(data => {
                updateCharts(data);
                updateDataStatus(data);
            })
            .catch(error => console.error('Error fetching data:', error));
    }

    function updateDataStatus(data) {
        const statusContainer = document.getElementById('dataStatus');
        if (statusContainer) {
            let statusHtml = `<strong>${data.station}</strong> (${data.station_code}) | `;

            data.days.forEach((day, idx) => {
                const statusIcon = day.is_complete ? '✓' : '⚠';
                const statusClass = day.is_complete ? 'complete' : 'incomplete';
                statusHtml += `<span class="day-status ${statusClass}">${statusIcon} ${day.label}</span>`;
                if (idx < data.days.length - 1) statusHtml += ' | ';
            });

            statusContainer.innerHTML = statusHtml;
            statusContainer.innerHTML = statusHtml;
        }

        const dateBadge = document.getElementById('todayDateBadge');
        if (dateBadge && data.today_live && data.today_live.date) {
            const dateObj = new Date(data.today_live.date);
            const options = { day: '2-digit', month: 'short', year: 'numeric', timeZone: 'UTC' };
            const dateStr = dateObj.toLocaleDateString('en-GB', options);
            dateBadge.textContent = `Today: ${dateStr} (UTC)`;
        } else if (dateBadge) {
            const now = new Date();
            const options = { day: '2-digit', month: 'short', year: 'numeric', timeZone: 'UTC' };
            dateBadge.textContent = `Today: ${now.toLocaleDateString('en-GB', options)} (UTC)`;
        }
    }

    function updateCharts(data) {
        const chartConfigs = [
            { id: 'tempChart', key: 'temperature', title: 'Temperature (°C)', yaxis: 'Temperature (°C)' },
            { id: 'dewChart', key: 'dew_point', title: 'Dew Point (°C)', yaxis: 'Dew Point (°C)' },
            { id: 'rhChart', key: 'relative_humidity', title: 'Relative Humidity (%)', yaxis: 'Humidity (%)' },
            { id: 'windSpeedChart', key: 'wind_speed', title: 'Wind Speed (kt)', yaxis: 'Wind Speed (kt)' },
            { id: 'windDirChart', key: 'wind_direction', title: 'Wind Direction (°)', yaxis: 'Direction (°)' },
            { id: 'visChart', key: 'visibility', title: 'Visibility (m)', yaxis: 'Visibility (m)' },
            { id: 'qnhChart', key: 'qnh', title: 'QNH Pressure (hPa)', yaxis: 'Pressure (hPa)' }
        ];

        chartConfigs.forEach(config => {
            const traces = [];

            data.days.forEach((dayData, index) => {
                addTrace(dayData, index, false);
            });

            if (data.today_live) {
                addTrace(data.today_live, 3, true);
            }

            function addTrace(dayData, index, isLive) {
                const xValues = dayData.data.map(obs => `2000-01-01 ${obs.time}`);
                const yValues = dayData.data.map(obs => obs[config.key]);

                let lineColor, lineDash, lineWidth;

                if (isLive) {
                    lineColor = 'rgb(220, 53, 69)';
                    lineDash = 'solid';
                    lineWidth = 3;
                } else {
                    lineColor = dayData.is_complete ? colors[index] : incompleteColors[index];
                    lineDash = 'dot';
                    lineWidth = 2;
                }

                traces.push({
                    x: xValues,
                    y: yValues,
                    type: 'scatter',
                    mode: 'lines+markers',
                    name: dayData.label,
                    line: {
                        color: lineColor,
                        width: lineWidth,
                        dash: lineDash
                    },
                    marker: {
                        size: isLive ? 6 : 4,
                        symbol: 'circle'
                    },
                    connectgaps: true,
                    hovertemplate: `<b>${dayData.label}</b><br>` +
                        `Time: %{x|%H:%M} UTC<br>` +
                        `${config.yaxis}: %{y}<br>` +
                        `<extra></extra>`
                });
            }

            const layout = {
                xaxis: {
                    title: 'Time (UTC)',
                    type: 'date',
                    tickformat: '%H:%M',
                    range: ['2000-01-01 00:00:00', '2000-01-01 23:59:59'],
                    dtick: 3 * 60 * 60 * 1000,
                    showgrid: true,
                    gridcolor: '#e0e0e0',
                    fixedrange: false
                },
                yaxis: {
                    title: config.yaxis,
                    showgrid: true,
                    gridcolor: '#e0e0e0',
                    fixedrange: false
                },
                margin: { t: 40, r: 30, b: 60, l: 70 },
                legend: {
                    orientation: 'h',
                    y: 1.12,
                    x: 0.5,
                    xanchor: 'center',
                    font: { size: 11 }
                },
                hovermode: 'x unified',
                plot_bgcolor: 'white',
                paper_bgcolor: 'white',
                shapes: [
                    {
                        type: 'line',
                        x0: '2000-01-01 00:00:00',
                        x1: '2000-01-01 00:00:00',
                        y0: 0,
                        y1: 1,
                        yref: 'paper',
                        line: { color: '#ccc', width: 1, dash: 'dot' }
                    },
                    {
                        type: 'line',
                        x0: '2000-01-01 12:00:00',
                        x1: '2000-01-01 12:00:00',
                        y0: 0,
                        y1: 1,
                        yref: 'paper',
                        line: { color: '#ccc', width: 1, dash: 'dot' }
                    }
                ]
            };

            const plotConfig = {
                responsive: true,
                displayModeBar: true,
                modeBarButtonsToRemove: ['lasso2d', 'select2d'],
                displaylogo: false,
                scrollZoom: true
            };

            Plotly.newPlot(config.id, traces, layout, plotConfig);
        });
    }

    const LIVE_UPDATE_INTERVAL = 10 * 60 * 1000;

    function fetchLiveData() {
        console.log("Fetching live data...");
        fetch(`/api/live_data?station=${selectedStation}`)
            .then(response => response.json())
            .then(data => {
                if (data.today_live) {
                    updateLiveTrace(data.today_live);
                }
            })
            .catch(error => console.error('Error fetching live data:', error));
    }

    function updateLiveTrace(liveData) {
        const todayDate = liveData.date;
        const currentUtcDate = new Date().toISOString().split('T')[0];

        const chartIds = ['tempChart', 'dewChart', 'windSpeedChart', 'windDirChart', 'visChart', 'qnhChart'];
        const chartConfigs = [
            { id: 'tempChart', key: 'temperature' },
            { id: 'dewChart', key: 'dew_point' },
            { id: 'rhChart', key: 'relative_humidity' },
            { id: 'windSpeedChart', key: 'wind_speed' },
            { id: 'windDirChart', key: 'wind_direction' },
            { id: 'visChart', key: 'visibility' },
            { id: 'qnhChart', key: 'qnh' }
        ];

        chartConfigs.forEach(config => {
            const chartDiv = document.getElementById(config.id);
            if (!chartDiv || !chartDiv.data) return;

            let traceIndex = chartDiv.data.findIndex(trace => trace.name === liveData.label);

            const xValues = liveData.data.map(obs => `2000-01-01 ${obs.time}`);
            const yValues = liveData.data.map(obs => obs[config.key]);

            if (traceIndex !== -1) {
                Plotly.restyle(config.id, {
                    x: [xValues],
                    y: [yValues]
                }, [traceIndex]);
            } else {
            }
        });
    }

    function fetchLatestMetar() {
        const container = document.getElementById('latestDataContent');
        if (!container) return;

        fetch(`/api/latest/${selectedStation}`)
            .then(res => res.json())
            .then(data => {
                if (data.status === 'success') {
                    const d = data.data;
                    const timeStr = d.timestamp_utc ? d.timestamp_utc.substring(11, 16) : '--:--';

                    container.innerHTML = `
                        <div class="data-row">Time: <strong>${timeStr} UTC</strong></div>
                        <div class="data-row">Wind: <strong>${d.wind_direction}° / ${d.wind_speed}kt</strong></div>
                        <div class="data-row">Vis: <strong>${d.visibility}m</strong> | Temp: <strong>${d.temperature}°C</strong></div>
                        <div class="metar-box">
                            ${d.raw_metar || 'No raw METAR available'}
                        </div>
                    `;
                } else {
                    container.innerHTML = `<p class="loading-text">No data available</p>`;
                }
            })
            .catch(err => {
                console.error("METAR fetch error:", err);
                container.innerHTML = `<p class="loading-text" style="color:red">Error loading data</p>`;
            });
    }

    function fetchSigmetStatus() {
        const container = document.getElementById('sigmetContent');
        if (!container) return;

        fetch('/api/sigmet/status')
            .then(res => res.json())
            .then(data => {
                if (data.is_active) {
                    container.innerHTML = `
                        <div class="sigmet-active" style="margin-bottom: 5px;">⚠️ Active SIGMET</div>
                        <div style="font-size: 0.9em; margin-bottom: 5px;">${data.phenomenon || 'Unknown'}</div>
                        <div style="font-size: 0.85em; color: #555;">Mumbai FIR (VABF)</div>
                        <a href="#" class="btn-open" style="margin-top: 10px; font-size: 0.85em; background: #d9534f;">Display SIGMET ↗</a>
                    `;
                } else {
                    container.innerHTML = `
                        <div class="sigmet-none" style="margin-bottom: 10px;">No Active SIGMET</div>
                        <div style="font-size: 0.9em; color: #777; margin-bottom: 5px;">Mumbai FIR (VABF)</div>
                        <div style="font-size: 0.8em; color: #aaa;">Last checked: ${data.last_checked ? data.last_checked.substring(11, 16) : '--:--'} UTC</div>
                        <a href="/static/img/sigmet_display.png" target="_blank" class="btn-open" style="margin-top: 10px; font-size: 0.85em;">Display SIGMET ↗</a>
                    `;
                }
            })
            .catch(err => {
                console.error("SIGMET fetch error:", err);
                container.innerHTML = `<p class="loading-text" style="color:red">Error checking SIGMET</p>`;
            });
    }
    fetchData();

    setInterval(fetchLiveData, LIVE_UPDATE_INTERVAL);

    refreshBtn.addEventListener('click', fetchData);
});
