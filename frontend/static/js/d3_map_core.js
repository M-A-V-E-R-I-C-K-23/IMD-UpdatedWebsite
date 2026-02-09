
window.D3MapCore = (function () {
    'use strict';

    let mainSvg, insetSvg, mapViewport;
    let mainProjection, insetProjection;
    let selectedAirportCode = null;
    let config = {};
    let airports = [];

    let activeAlerts = {};
    let blinkState = true;
    let blinkInterval = null;
    let dataPollInterval = null;

    let canvas, context;
    let cachedPath2D = null;
    let currentTransform = d3.zoomIdentity;

    const FIR_DATA = {
        mumbai: {
            type: "Feature",
            properties: { name: "Mumbai FIR" },
            geometry: {
                type: "Polygon",
                coordinates: [[
                    [79.0819, 25.0003], [70.9167, 25.0000], [68.1667, 23.6667],
                    [68.3833, 23.5000], [64.5000, 23.5000], [60.0000, 19.8000],
                    [60.0000, -6.0000], [68.0000, -6.0000], [68.0000, 0.0000],
                    [70.0000, 3.0833], [70.0000, 7.5000], [72.0000, 7.5000],
                    [72.0000, 15.0000], [73.5833, 15.0000], [74.0000, 15.5000],
                    [77.0000, 17.0000], [80.0000, 18.0000], [82.0000, 22.0000],
                    [79.0819, 25.0003]
                ]]
            }
        }
    };

    function init(containerSelector, airportData, options) {
        airports = airportData || [];
        config = options || {};

        mainSvg = d3.select(containerSelector);
        mapViewport = document.getElementById('map-viewport') || document.querySelector('.map-wrapper');

        if (!mainSvg.node() || !mapViewport) {
            console.error('D3MapCore: Container not found');
            return;
        }

        setupMap();
    }

    async function setupMap() {
        console.log('[D3 Map] Starting setup...');
        console.log('[D3 Map] Viewport element:', mapViewport);

        const width = mapViewport ? mapViewport.clientWidth : 800;
        const height = mapViewport ? mapViewport.clientHeight : 600;

        console.log('[D3 Map] Dimensions:', { width, height });

        mainProjection = d3.geoMercator()
            .center([75, 18.2])
            .scale(800)
            .translate([width / 2, height / 2]);

        const path = d3.geoPath().projection(mainProjection);

        try {
            const url = config.geojsonUrl || '/static/geojson/india_state.geojson';
            console.log('[D3 Map] Fetching GeoJSON from:', url);
            const response = await fetch(url);
            if (!response.ok) throw new Error(`GeoJSON fetch failed: ${response.status}`);
            const geoData = await response.json();
            console.log('[D3 Map] GeoJSON loaded, features:', geoData.features ? geoData.features.length : 0);

            const zoomLayer = mainSvg.append("g").attr("id", "zoom-container");
            console.log('[D3 Map] Zoom layer created');

            setupCanvasLayer(width, height);

            let rafId = null;

            const scheduleDraw = () => {
                if (rafId) return;
                rafId = requestAnimationFrame(() => {
                    drawMarkers(currentTransform);
                    rafId = null;
                });
            };

            const zoom = d3.zoom()
                .scaleExtent([0.5, 8])
                .on("start", () => {
                    d3.select(".d3-map-scoped").classed("is-zooming", true);
                })
                .on("zoom", (event) => {
                    currentTransform = event.transform;

                    zoomLayer.attr("transform", event.transform);
                    updateScaleBar(event.transform.k, width, height);

                    scheduleDraw();
                })
                .on("end", () => {
                    d3.select(".d3-map-scoped").classed("is-zooming", false);
                });

            canvas.call(zoom);
            console.log('[D3 Map] Zoom behavior attached to Canvas');

            const initialZoom = 2.5;
            const centerX = width / 2;
            const centerY = height / 2;
            const transform = d3.zoomIdentity
                .translate(centerX, centerY)
                .scale(initialZoom)
                .translate(-centerX, -centerY);

            canvas.call(zoom.transform, transform);
            console.log('[D3 Map] Applied initial zoom:', initialZoom);

            console.log('[D3 Map] Rendering layer with', airports.length, 'airports');
            renderLayer(zoomLayer, geoData, path);

            startAlertSystem();

            airports.forEach(a => {
                const coords = mainProjection([a.long, a.lat]);
                if (coords) {
                    a.x = coords[0];
                    a.y = coords[1];
                }
            });

            currentTransform = transform;
            drawMarkers(transform);

            d3.select("#zoom-in").on("click", () => canvas.call(zoom.scaleBy, 1.5));
            d3.select("#zoom-out").on("click", () => canvas.call(zoom.scaleBy, 0.6));
            d3.select("#zoom-reset").on("click", () => {
                const resetTransform = d3.zoomIdentity
                    .translate(width / 2, height / 2)
                    .scale(2.5)
                    .translate(-width / 2, -height / 2);
                canvas.transition().call(zoom.transform, resetTransform);
            });

            updateScaleBar(2.5, width, height);

        } catch (error) {
            console.error("Map Setup Failed:", error);
            if (config.onError) config.onError(error);
        }
    }

    function setupCanvasLayer(w, h) {
        const container = d3.select(mainSvg.node().parentNode);

        container.select("canvas").remove();

        canvas = container.append("canvas")
            .attr("width", w)
            .attr("height", h)
            .style("position", "absolute")
            .style("top", "0")
            .style("left", "0")
            .style("pointer-events", "auto");

        context = canvas.node().getContext('2d');

        const dpr = window.devicePixelRatio || 1;
        canvas.attr("width", w * dpr).attr("height", h * dpr);
        canvas.style("width", `${w}px`).style("height", `${h}px`);
        context.scale(dpr, dpr);

        cachedPath2D = new Path2D("M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7z");

        canvas.on("click", handleCanvasClick);
    }

    function drawMarkers(transform) {
        if (!context) return;

        const w = parseFloat(canvas.style("width"));
        const h = parseFloat(canvas.style("height"));

        context.clearRect(0, 0, w, h);

        context.save();
        context.translate(transform.x, transform.y);
        context.scale(transform.k, transform.k);

        const baseScale = 1.0;
        const pinScale = Math.min(2.0, Math.max(0.2, 1.6 / transform.k));

        context.textAlign = "center";
        context.font = "600 7px sans-serif";
        context.lineJoin = "round";

        airports.forEach(airport => {
            if (!airport.x || !airport.y) return;

            context.save();
            context.translate(airport.x, airport.y);
            context.scale(pinScale, pinScale);

            context.translate(-12, -22);

            let pinColor = "#FFD60A";
            let isDimmed = false;
            let hasAlert = false;

            let code = airport.code;
            if (typeof code === 'string') code = code.trim();

            if (activeAlerts[code]) {
                hasAlert = true;
                pinColor = "#ef4444";

                if (activeAlerts[code].isUrgent && !blinkState) {
                    isDimmed = true;
                }
            }

            context.fillStyle = pinColor;
            context.strokeStyle = "#FFFFFF";
            context.lineWidth = 1.5;

            if (isDimmed) {
                context.globalAlpha = 0.4;
            }

            if (selectedAirportCode === airport.code) {
                context.shadowBlur = 15;
                context.shadowColor = "#FFD60A";
            } else {
                context.shadowBlur = 0;
            }

            if (selectedAirportCode === airport.code) {
                context.strokeStyle = "#fff";
                context.lineWidth = 2.5;
            }

            context.fill(cachedPath2D);
            context.stroke(cachedPath2D);

            context.beginPath();
            context.arc(12, 9, 3, 0, 2 * Math.PI);
            context.fillStyle = "#fff";
            context.fill();

            context.shadowBlur = 0;
            context.lineWidth = 2.5;
            context.strokeStyle = "#07090F";
            context.fillStyle = "#F8F9FA";

            context.strokeText(airport.code, 12, -5);
            context.fillText(airport.code, 12, -5);

            if (isDimmed) {
                context.globalAlpha = 1.0;
            }

            context.restore();
        });

        context.restore();
    }

    function handleCanvasClick(event) {
        if (!currentTransform) return;

        const [mx, my] = d3.pointer(event, this);

        const wx = (mx - currentTransform.x) / currentTransform.k;
        const wy = (my - currentTransform.y) / currentTransform.k;

        let nearest = null;
        let minDist = Infinity;
        const threshold = 20 / currentTransform.k;

        airports.forEach(a => {
            const dx = a.x - wx;
            const dy = a.y - wy;
            const dist = Math.sqrt(dx * dx + dy * dy);
            if (dist < minDist) {
                minDist = dist;
                nearest = a;
            }
        });

        if (nearest && minDist < threshold) {
            handleAirportClick(nearest);
        }
    }

    function renderLayer(target, geoData, geoPath) {
        target.selectAll(".state-color")
            .data(geoData.features)
            .enter()
            .append("path")
            .attr("d", geoPath)
            .attr("class", "state-color muted");

        if (config.showFIR !== false) {
            target.append("path")
                .datum(FIR_DATA.mumbai)
                .attr("d", geoPath)
                .attr("class", "fir-boundary fir-mumbai");
        }

        const graticule = d3.geoGraticule().step([5, 5]);
        target.append("path")
            .datum(graticule)
            .attr("class", "graticule")
            .attr("d", geoPath);
    }

    function handleAirportClick(airport) {
        console.log('Airport clicked:', airport.code);
        selectedAirportCode = airport.code;

        drawMarkers(currentTransform);

        if (config.onAirportClick) {
            config.onAirportClick(airport);
        } else {
            window.location.href = `/dashboard/${airport.code}`;
        }
    }

    function updateScaleBar(k, width, height) {
        const center = mainProjection.invert([width / 2, height / 2]);
        const p1 = mainProjection.invert([width / 2, height / 2]);
        const p2 = mainProjection.invert([width / 2 + 100 / k, height / 2]);

        if (p1 && p2) {
            const R = 6371;
            const dLat = (p2[1] - p1[1]) * Math.PI / 180;
            const dLon = (p2[0] - p1[0]) * Math.PI / 180;
            const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
                Math.cos(p1[1] * Math.PI / 180) * Math.cos(p2[1] * Math.PI / 180) *
                Math.sin(dLon / 2) * Math.sin(dLon / 2);
            const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
            const d = R * c;

            const niceNumbers = [10, 20, 50, 100, 200, 500, 1000, 2000, 5000];
            let displayKm = 500;
            let displayPx = 100;

            for (let num of niceNumbers) {
                const px = (100 * num) / d;
                if (px >= 60 && px <= 180) {
                    displayKm = num;
                    displayPx = px;
                    break;
                }
            }

            const scaleBarLine = document.getElementById("scale-bar-line");
            const scaleBarText = document.getElementById("scale-bar-text");
            if (scaleBarLine && scaleBarText) {
                scaleBarLine.style.width = `${displayPx}px`;
                scaleBarText.innerText = `${displayKm} km`;
            }
        }
    }

    function startAlertSystem() {
        console.log('[D3 Map] Starting alert polling...');
        fetchActiveWarnings();

        dataPollInterval = setInterval(fetchActiveWarnings, 30000);

        setInterval(updateUrgencyStatus, 1000);

        blinkInterval = setInterval(() => {
            blinkState = !blinkState;
            const hasUrgent = Object.values(activeAlerts).some(a => a.isUrgent);
            if (hasUrgent) {
                drawMarkers(currentTransform);
            }
        }, 500);
    }

    async function fetchActiveWarnings() {
        try {
            const response = await fetch('/api/warnings/active');
            const result = await response.json();

            if (result.success) {
                const newAlerts = {};
                const now = new Date();

                result.data.forEach(w => {
                    let isoStr = w.valid_to.replace(' ', 'T');
                    if (!isoStr.endsWith('Z')) isoStr += 'Z';

                    let key = w.station_icao;
                    if (typeof key === 'string') key = key.trim().toUpperCase();

                    const validToDate = new Date(isoStr);
                    newAlerts[key] = {
                        validTo: validToDate,
                        isUrgent: false
                    };
                });

                const SENDER_CODE = 'VABB';
                const alertKeys = Object.keys(newAlerts);

                if (alertKeys.length > 0) {
                    let maxValidTo = new Date(0);

                    Object.values(newAlerts).forEach(a => {
                        if (a.validTo > maxValidTo) maxValidTo = a.validTo;
                    });

                    if (!newAlerts[SENDER_CODE]) {
                        newAlerts[SENDER_CODE] = {
                            validTo: maxValidTo,
                            isUrgent: false,
                            isSender: true
                        };
                    } else {
                        if (maxValidTo > newAlerts[SENDER_CODE].validTo) {
                            newAlerts[SENDER_CODE].validTo = maxValidTo;
                        }
                    }
                }

                activeAlerts = newAlerts;
                updateUrgencyStatus();
                drawMarkers(currentTransform);
            }
        } catch (e) {
            console.error("[D3 Map] Alert fetch error", e);
        }
    }

    function updateUrgencyStatus() {
        const now = new Date();
        let changed = false;

        for (const [code, warning] of Object.entries(activeAlerts)) {
            if (warning.validTo < now) {
                delete activeAlerts[code];
                changed = true;
                continue;
            }

            const timeDiff = warning.validTo - now;
            const isUrgent = timeDiff <= 30 * 60 * 1000;

            if (warning.isUrgent !== isUrgent) {
                warning.isUrgent = isUrgent;
                changed = true;
            }
        }

        if (changed) {
            drawMarkers(currentTransform);
        }
    }

    return {
        init: init
    };
})();
