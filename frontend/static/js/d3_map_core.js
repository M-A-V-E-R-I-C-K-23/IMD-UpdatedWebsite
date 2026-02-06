/**
 * D3 Map Core Module
 * Adapted from map_bc repository for IMD dashboard integration
 * This module renders a D3-based map of India with airport markers
 */

window.D3MapCore = (function () {
    'use strict';

    let mainSvg, insetSvg, mapViewport;
    let mainProjection, insetProjection;
    let selectedAirportCode = null;
    let config = {};
    let airports = [];

    // Canvas vars
    let canvas, context;
    let cachedPath2D = null;
    let currentTransform = d3.zoomIdentity;

    // FIR Boundaries (hardcoded)
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

        // Configure projections
        mainProjection = d3.geoMercator()
            .center([75, 18.2]) // Centered on Maharashtra airports (based on screenshot)
            .scale(800)
            .translate([width / 2, height / 2]);

        const path = d3.geoPath().projection(mainProjection);

        try {
            // Fetch GeoJSON
            const url = config.geojsonUrl || '/static/geojson/india_state.geojson';
            console.log('[D3 Map] Fetching GeoJSON from:', url);
            const response = await fetch(url);
            if (!response.ok) throw new Error(`GeoJSON fetch failed: ${response.status}`);
            const geoData = await response.json();
            console.log('[D3 Map] GeoJSON loaded, features:', geoData.features ? geoData.features.length : 0);

            // Setup zoom layer
            const zoomLayer = mainSvg.append("g").attr("id", "zoom-container");
            console.log('[D3 Map] Zoom layer created');

            // --- SETUP CANVAS LAYER ---
            setupCanvasLayer(width, height);

            // Configure zoom behavior
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

                    // Transform SVG Layer (Static Paths)
                    zoomLayer.attr("transform", event.transform);
                    updateScaleBar(event.transform.k, width, height);

                    // Schedule Canvas Redraw
                    scheduleDraw();
                })
                .on("end", () => {
                    d3.select(".d3-map-scoped").classed("is-zooming", false);
                    // Labels are drawn in drawMarkers now
                });

            // IMPORTANT: Attach zoom to CANVAS, as it is the top-most layer capturing events
            canvas.call(zoom);
            console.log('[D3 Map] Zoom behavior attached to Canvas');

            // Set initial zoom to show 200 km scale bar (instead of default 500 km)
            // Center the zoom on Maharashtra coordinates
            const initialZoom = 2.5;
            const centerX = width / 2;
            const centerY = height / 2;
            const transform = d3.zoomIdentity
                .translate(centerX, centerY)
                .scale(initialZoom)
                .translate(-centerX, -centerY);

            // Apply initial state to CANVAS
            canvas.call(zoom.transform, transform);
            console.log('[D3 Map] Applied initial zoom:', initialZoom);

            // Render SVG base layers (States, FIR)
            console.log('[D3 Map] Rendering layer with', airports.length, 'airports');
            renderLayer(zoomLayer, geoData, path);

            // Pre-Calculate Airport Positions (Project once)
            airports.forEach(a => {
                const coords = mainProjection([a.long, a.lat]);
                if (coords) {
                    a.x = coords[0];
                    a.y = coords[1];
                }
            });

            // Initial Canvas Draw
            currentTransform = transform;
            drawMarkers(transform);

            // Setup controls - Must act on CANVAS selection now
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
        // Create canvas if not exists
        const container = d3.select(mainSvg.node().parentNode);

        // Remove old if any
        container.select("canvas").remove();

        canvas = container.append("canvas")
            .attr("width", w)
            .attr("height", h)
            .style("position", "absolute")
            .style("top", "0")
            .style("left", "0")
            .style("pointer-events", "auto"); // IMPORTANT for clicks

        context = canvas.node().getContext('2d');

        // Handle Device Pixel Ratio for sharp rendering
        const dpr = window.devicePixelRatio || 1;
        canvas.attr("width", w * dpr).attr("height", h * dpr);
        canvas.style("width", `${w}px`).style("height", `${h}px`);
        context.scale(dpr, dpr);

        // Pre-compile Path2D for marker
        // Droplet path: M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7z
        // Centered roughly at 12, 22. We translate it to center at 0,0 for easier drawing
        // Translate -12, -22 to match SVG
        cachedPath2D = new Path2D("M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7z");

        // Add click listener to canvas
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

        // Inverse scaling: pins shrink when zooming IN
        const baseScale = 1.0; // Adjusted from SVG 1.6 to match standard canvas size
        const pinScale = Math.min(2.0, Math.max(0.2, 1.6 / transform.k)); // Reuse logic

        // Label settings (Pin Space)
        context.textAlign = "center";
        context.font = "600 7px sans-serif"; // Target ~11px screen size
        context.lineJoin = "round";

        airports.forEach(airport => {
            if (!airport.x || !airport.y) return;

            context.save();
            context.translate(airport.x, airport.y);
            context.scale(pinScale, pinScale);

            // 1. Draw Pin
            context.translate(-12, -22); // Re-align Path2D origin
            context.fillStyle = "#2563eb"; // Blue
            context.strokeStyle = "rgba(255, 255, 255, 0.8)";
            context.lineWidth = 1;

            if (selectedAirportCode === airport.code) {
                context.strokeStyle = "#fff";
                context.lineWidth = 2.5;
                context.shadowBlur = 10;
                context.shadowColor = "#38bdf8";
            }

            context.fill(cachedPath2D);
            context.stroke(cachedPath2D);

            // 2. Draw Center Dot
            context.beginPath();
            context.arc(12, 9, 3, 0, 2 * Math.PI); // Relative to new origin
            context.fillStyle = "#fff";
            context.fill();

            // 3. Draw Label (Relative to Pin Origin 12, 22)
            // Pin visual top is around (12, 2). Place label centered above.
            // Using offset (12, -6) in Pin Space
            context.lineWidth = 2.5; // Stroke width for text halo
            context.strokeStyle = "#0f172a"; // Dark halo
            context.fillStyle = "#f1f5f9"; // Light text

            // Note: fillText arguments are (text, x, y) in current transform system
            // We want it centered at x=12, y=-6 relative to the -12,-22 translated origin
            // Actually, we are currently translated to (-12, -22). 
            // So center of pin is at (12, 22) relative to this.
            // Wait, previous dot was at (12, 9) relative to this new origin.
            // So x=12 is horizontal center.
            // y=2 is top of pin in Path definition "M12 2..."
            // So we want label above y=2. Say y=-5.

            context.strokeText(airport.code, 12, -5);
            context.fillText(airport.code, 12, -5);

            context.restore();
        });

        context.restore();
    }


function handleCanvasClick(event) {
    if (!currentTransform) return;

    // Get mouse position relative to canvas
    const [mx, my] = d3.pointer(event, this);

    // Invert transform to get world coordinates
    const wx = (mx - currentTransform.x) / currentTransform.k;
    const wy = (my - currentTransform.y) / currentTransform.k;

    // Find nearest airport
    // Simple distance check (N is small, < 100 usually)
    let nearest = null;
    let minDist = Infinity;
    const threshold = 20 / currentTransform.k; // Hit radius approx 20px screen space

    airports.forEach(a => {
        const dx = a.x - wx;
        const dy = a.y - wy; // Pin acts as if centered at bottom, so wy is fine
        // Actually pin center is at y-11 approx. 
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
    // Draw states
    target.selectAll(".state-color")
        .data(geoData.features)
        .enter()
        .append("path")
        .attr("d", geoPath)
        .attr("class", "state-color muted");

    // Draw FIR boundary (Mumbai)
    if (config.showFIR !== false) {
        target.append("path")
            .datum(FIR_DATA.mumbai)
            .attr("d", geoPath)
            .attr("class", "fir-boundary fir-mumbai");
    }

    // Draw graticule
    const graticule = d3.geoGraticule().step([5, 5]);
    target.append("path")
        .datum(graticule)
        .attr("class", "graticule")
        .attr("d", geoPath);

    // NO SVG AIRPORTS RENDERED HERE
}

function handleAirportClick(airport) {
    console.log('Airport clicked:', airport.code);
    selectedAirportCode = airport.code;

    // Redraw to show selection highlight
    drawMarkers(currentTransform);

    // Fire event or callback
    if (config.onAirportClick) {
        config.onAirportClick(airport);
    } else {
        // Default: navigate to dashboard
        window.location.href = `/dashboard/${airport.code}`;
    }
}

function updateScaleBar(k, width, height) {
    const center = mainProjection.invert([width / 2, height / 2]);
    const p1 = mainProjection.invert([width / 2, height / 2]);
    const p2 = mainProjection.invert([width / 2 + 100 / k, height / 2]);

    if (p1 && p2) {
        const R = 6371; // Earth radius in km
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

return {
    init: init
};
}) ();
