
document.addEventListener('DOMContentLoaded', function () {
    const selectedStation = window.SELECTED_STATION;
    const refreshBtn = document.getElementById('refreshBtn');

    // Runway configuration (Heading 1 / Heading 2)
    const RUNWAY_INFO = {
        "VABB": { rwy1: 27, rwy2: 9, label: "27/09" },
        "VAAH": { rwy1: 23, rwy2: 5, label: "23/05" },
        "VANP": { rwy1: 32, rwy2: 14, label: "32/14" },
        "VABO": { rwy1: 22, rwy2: 4, label: "22/04" },
        "VAID": { rwy1: 25, rwy2: 7, label: "25/07" },
        "VABP": { rwy1: 30, rwy2: 12, label: "30/12" },
        "VAGO": { rwy1: 26, rwy2: 8, label: "26/08" },
        "VAOZ": { rwy1: 26, rwy2: 8, label: "26/08" }, // Approx
        "VAAU": { rwy1: 27, rwy2: 9, label: "27/09" }, // Approx
        "VAKP": { rwy1: 28, rwy2: 10, label: "28/10" },
        "VASN": { rwy1: 28, rwy2: 10, label: "28/10" }, // Approx
        "VASU": { rwy1: 4, rwy2: 22, label: "04/22" },
        "VAJJ": { rwy1: 26, rwy2: 8, label: "26/08" }
    };

    function drawRunwayDial(windDir, windSpeed) {
        const config = RUNWAY_INFO[selectedStation] || { rwy1: 27, rwy2: 9, label: "27/09" };
        const runwayHeading = config.rwy1 * 10;

        // Calculate components
        const radd = (windDir - runwayHeading) * Math.PI / 180;
        const headwind = (windSpeed * Math.cos(radd)).toFixed(1);
        const crosswind = (windSpeed * Math.sin(radd)).toFixed(1);

        const data = [
            // Wind Vector Arrow
            {
                type: 'scatterpolar',
                r: [0, windSpeed],
                theta: [0, windDir],
                mode: 'lines+markers',
                line: { color: 'red', width: 4 },
                marker: { symbol: 'arrow-bar-up', size: 15, color: 'red' },
                name: 'Wind'
            },
            // Runway Strip
            {
                type: 'scatterpolar',
                r: [30, 30], // Length of runway visual
                theta: [runwayHeading, runwayHeading + 180],
                mode: 'lines',
                line: { color: 'black', width: 20 },
                name: 'Runway',
                hoverinfo: 'none'
            }
        ];

        const layout = {
            polar: {
                radialaxis: { visible: true, range: [0, Math.max(40, windSpeed + 10)] },
                angularaxis: {
                    direction: "clockwise",
                    rotation: 90,
                    tickmode: "array",
                    tickvals: [0, 90, 180, 270],
                    ticktext: ["N", "E", "S", "W"]
                }
            },
            showlegend: false,
            title: {
                text: `Runway ${config.label}<br><span style="font-size:0.8em; color:blue">Head/Tail: ${headwind}kt | Cross: ${Math.abs(crosswind)}kt</span>`,
                font: { size: 14 }
            },
            margin: { t: 40, b: 30, l: 40, r: 40 },
            autosize: true
        };

        Plotly.newPlot('runwayDial', data, layout, { displayModeBar: false, responsive: true });
    }

    function drawSpeedDial(windSpeed) {
        const data = [
            {
                type: "indicator",
                mode: "gauge+number",
                value: windSpeed,
                title: { text: "Speed (kt)", font: { size: 14 } },
                gauge: {
                    axis: { range: [null, 60], tickwidth: 1, tickcolor: "darkblue" },
                    bar: { color: "#0056b3" },
                    bgcolor: "white",
                    borderwidth: 2,
                    bordercolor: "gray",
                    steps: [
                        { range: [0, 15], color: "#e3f2fd" },
                        { range: [15, 30], color: "#bbdefb" },
                        { range: [30, 60], color: "#90caf9" }
                    ],
                    threshold: {
                        line: { color: "red", width: 4 },
                        thickness: 0.75,
                        value: 50
                    }
                }
            }
        ];

        const layout = {
            margin: { t: 30, b: 30, l: 30, r: 30 },
            autosize: true
        };

        Plotly.newPlot('speedDial', data, layout, { displayModeBar: false, responsive: true });
    }

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
                if (data.today_live && data.today_live.data && data.today_live.data.length > 0) {
                    const lastObs = data.today_live.data[data.today_live.data.length - 1];
                    drawRunwayDial(lastObs.wind_direction, lastObs.wind_speed);
                    drawSpeedDial(lastObs.wind_speed);
                }
            })
            .catch(error => console.error('Error fetching data:', error));
    }

    function updateDataStatus(data) {
        const statusContainer = document.getElementById('dataStatusContent');
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
            }
        });

        if (liveData.data && liveData.data.length > 0) {
            const lastObs = liveData.data[liveData.data.length - 1];
            drawRunwayDial(lastObs.wind_direction, lastObs.wind_speed);
            drawSpeedDial(lastObs.wind_speed);
        }
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
