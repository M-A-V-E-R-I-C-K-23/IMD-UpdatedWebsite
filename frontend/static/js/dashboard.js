
document.addEventListener('DOMContentLoaded', function () {
    const selectedStation = window.SELECTED_STATION;
    const refreshBtn = document.getElementById('refreshBtn');

    // ── Runway Wind Compass ─────────────────────────────────────────────────

    const RUNWAY_DATA = {
        "VABB": [{ name: "09/27", heading: 90  }, { name: "14/32", heading: 140 }],  // Mumbai
        "VASD": [{ name: "09/27", heading: 90  }],  // Shirdi
        "VAJJ": [{ name: "08/26", heading: 80  }],  // Juhu
        "VAJL": [{ name: "08/26", heading: 80  }],  // Jalgaon
        "VAAU": [{ name: "09/27", heading: 90  }],  // Aurangabad
        "VOND": [{ name: "09/27", heading: 90  }],  // Nanded
        "VAKP": [{ name: "08/26", heading: 80  }],  // Kolhapur
        "VOSR": [{ name: "04/22", heading: 40  }],  // Sindhudurg
        "VASL": [{ name: "08/26", heading: 80  }],  // Solapur
        "VOLT": [{ name: "09/27", heading: 90  }],  // Latur
        "VOGA": [{ name: "09/27", heading: 90  }],  // Mopa (Goa)
        "VANM": [{ name: "08/26", heading: 80  }]   // Navi Mumbai
    };

    /**
     * Build one SVG compass element for a single runway.
     * Wind arrow points FROM the wind's origin (aviation standard).
     * All SVG rotations use explicit center pivot (cx, cy) to prevent drift.
     *
     * @param {object} runway      - { name: string, heading: number° }
     * @param {number} windDir     - observed wind direction in degrees (0-359)
     * @param {number} windSpeed   - observed wind speed in knots
     * @returns {HTMLElement}      - .compass-wrapper div containing SVG + data row
     */
    function createCompass(runway, windDir, windSpeed) {
        const cx = 100, cy = 100, R = 85;
        const runwayHeading = runway.heading;

        // ① Angle normalization — prevents 0°/360° boundary bugs
        const relativeAngle = (windDir - runwayHeading + 360) % 360;
        const angleRad = relativeAngle * Math.PI / 180;
        const headwind  = windSpeed * Math.cos(angleRad);
        const crosswind = windSpeed * Math.sin(angleRad);

        // ④ Crosswind direction label
        const crossDir = crosswind >= 0 ? 'Right' : 'Left';
        const headLabel = headwind >= 0
            ? `HW: ${Math.abs(headwind).toFixed(1)}kt`
            : `TW: ${Math.abs(headwind).toFixed(1)}kt`;
        const crossLabel = `XW: ${Math.abs(crosswind).toFixed(1)}kt (${crossDir})`;

        // Runway strip endpoints (±half-length along heading, rotated to heading)
        // ③ Center-pivot rotation: rotate(angle, cx, cy)
        const rLen = 60;

        // Tick marks for compass bezel
        let ticks = '';
        for (let i = 0; i < 36; i++) {
            const isMajor = i % 9 === 0;
            const tickLen = isMajor ? 10 : 5;
            const angle = i * 10 * Math.PI / 180;
            const x1 = cx + R * Math.sin(angle);
            const y1 = cy - R * Math.cos(angle);
            const x2 = cx + (R - tickLen) * Math.sin(angle);
            const y2 = cy - (R - tickLen) * Math.cos(angle);
            ticks += `<line x1="${x1.toFixed(1)}" y1="${y1.toFixed(1)}" x2="${x2.toFixed(1)}" y2="${y2.toFixed(1)}" stroke="#1a2a4a" stroke-width="${isMajor ? 2 : 1}"/>`;
        }

        // Cardinal labels
        const cardinals = [
            { label: 'N', dx: 0,    dy: -68 },
            { label: 'E', dx: 68,   dy: 0   },
            { label: 'S', dx: 0,    dy: 72  },
            { label: 'W', dx: -72,  dy: 0   }
        ];
        const cardinalSvg = cardinals.map(c =>
            `<text x="${cx + c.dx}" y="${cy + c.dy}" text-anchor="middle" dominant-baseline="middle"
                   font-size="11" font-weight="700" fill="#1a2a4a" font-family="Roboto,sans-serif">${c.label}</text>`
        ).join('');

        // ② Wind arrow: points FROM wind origin (aviation convention)
        //    Arrow shaft + arrowhead, ③ rotated around center
        const arrowLen = Math.min(70, 20 + windSpeed * 2.5);
        const arrowSvg = windSpeed > 0 ? `
            <g transform="rotate(${windDir}, ${cx}, ${cy})">
                <line x1="${cx}" y1="${cy}" x2="${cx}" y2="${cy - arrowLen}"
                      stroke="#e63946" stroke-width="2.5" stroke-linecap="round"/>
                <polygon points="${cx},${cy - arrowLen - 2} ${cx - 6},${cy - arrowLen + 10} ${cx + 6},${cy - arrowLen + 10}"
                         fill="#e63946"/>
            </g>` : '';

        // Runway strip: thick line rotated to runway heading, ③ center pivot
        // Runway number labels at both ends
        const rwyParts = runway.name.split('/');
        const rwy1Label = rwyParts[0] || '';
        const rwy2Label = rwyParts[1] || '';
        const runwaySvg = `
            <g transform="rotate(${runwayHeading}, ${cx}, ${cy})">
                <line x1="${cx}" y1="${cy - rLen}" x2="${cx}" y2="${cy + rLen}"
                      stroke="#5a5a5a" stroke-width="10" stroke-linecap="round"/>
                <!-- threshold markings -->
                <line x1="${cx - 5}" y1="${cy - rLen + 4}" x2="${cx + 5}" y2="${cy - rLen + 4}"
                      stroke="white" stroke-width="1.5"/>
                <line x1="${cx - 5}" y1="${cy + rLen - 4}" x2="${cx + 5}" y2="${cy + rLen - 4}"
                      stroke="white" stroke-width="1.5"/>
                <text x="${cx}" y="${cy - rLen - 8}" text-anchor="middle" font-size="9"
                      font-weight="700" fill="#1a2a4a" font-family="Roboto,sans-serif">${rwy1Label}</text>
                <text x="${cx}" y="${cy + rLen + 14}" text-anchor="middle" font-size="9"
                      font-weight="700" fill="#1a2a4a" font-family="Roboto,sans-serif">${rwy2Label}</text>
            </g>`;

        // Assemble SVG — ⑥ viewBox for fluid responsiveness
        const svgHtml = `
        <svg class="compass-svg" viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
            <!-- Outer bezel -->
            <circle cx="${cx}" cy="${cy}" r="${R}" fill="#f7f9fc" stroke="#1a2a4a" stroke-width="2"/>
            <!-- Inner reference circle -->
            <circle cx="${cx}" cy="${cy}" r="4" fill="#1a2a4a"/>
            ${ticks}
            ${cardinalSvg}
            ${runwaySvg}
            ${arrowSvg}
        </svg>`;

        // Data badges
        const dataHtml = `
        <div class="compass-data">
            <span class="compass-hw">${headLabel}</span>
            <span class="compass-xw">${crossLabel}</span>
            <span class="compass-wind">Wind: ${windDir}° / ${windSpeed}kt</span>
        </div>`;

        const wrapper = document.createElement('div');
        wrapper.className = 'compass-wrapper';
        wrapper.innerHTML = `
            <div class="compass-caption">RWY ${runway.name} &nbsp;|&nbsp; ${runwayHeading}°</div>
            ${svgHtml}
            ${dataHtml}`;
        return wrapper;
    }

    /**
     * Render compass(es) for an airport into #runwayCompassContainer.
     * ⑤ Graceful fallback for airports not in RUNWAY_DATA.
     * ⑦ Clears container once, re-renders — no nested wrapper buildup.
     *
     * @param {string} airportCode
     * @param {number} windDir
     * @param {number} windSpeed
     */
    function renderRunwayCompasses(airportCode, windDir, windSpeed) {
        const container = document.getElementById('runwayCompassContainer');
        if (!container) return;

        // ⑦ Single clear
        container.innerHTML = '';

        // ⑤ Graceful fallback
        if (!RUNWAY_DATA[airportCode]) {
            container.innerHTML = "<div class='no-runway'>No runway data available for this station.</div>";
            return;
        }

        const runways = RUNWAY_DATA[airportCode];

        // Layout rules
        if (runways.length === 1) {
            container.classList.add('compass-single');
            container.classList.remove('compass-dual', 'compass-grid');
        } else if (runways.length === 2) {
            container.classList.add('compass-dual');
            container.classList.remove('compass-single', 'compass-grid');
        } else {
            container.classList.add('compass-grid');
            container.classList.remove('compass-single', 'compass-dual');
        }

        runways.forEach(runway => {
            container.appendChild(createCompass(runway, windDir, windSpeed));
        });
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

                // Try today's live data first
                let lastObs = null;
                if (data.today_live && data.today_live.data && data.today_live.data.length > 0) {
                    lastObs = data.today_live.data[data.today_live.data.length - 1];
                } else if (data.days && data.days.length > 0) {
                    // Fallback: use most recent observation from historical days
                    for (let i = data.days.length - 1; i >= 0; i--) {
                        if (data.days[i].data && data.days[i].data.length > 0) {
                            lastObs = data.days[i].data[data.days[i].data.length - 1];
                            break;
                        }
                    }
                }

                if (lastObs) {
                    renderRunwayCompasses(selectedStation, lastObs.wind_direction, lastObs.wind_speed);
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
            renderRunwayCompasses(selectedStation, lastObs.wind_direction, lastObs.wind_speed);
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
