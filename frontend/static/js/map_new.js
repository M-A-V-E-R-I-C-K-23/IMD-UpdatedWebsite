/**
 * MapCore - D3.js Map Engine
 * Handles rendering, zooming, and pin interactions.
 * Configured by MapAdapter.
 */

window.MapCore = (function () {
    let mainSvg, insetSvg, mapViewport;
    let mainProjection, insetProjection, zoomLayer;
    let stations = [];
    let geoData = null;

    // FIR Definitions
    const mumbaiFIR = {
        type: "Feature", properties: { name: "Mumbai FIR" },
        geometry: {
            type: "Polygon", coordinates: [[
                [79.0819, 25.0003], [70.9167, 25.0000], [68.1667, 23.6667], [68.3833, 23.5000],
                [64.5000, 23.5000], [60.0000, 19.8000], [60.0000, -6.0000], [68.0000, -6.0000],
                [68.0000, 0.0000], [70.0000, 3.0833], [70.0000, 7.5000], [72.0000, 7.5000],
                [72.0000, 15.0000], [73.5833, 15.0000], [74.0000, 15.5000], [77.0000, 17.0000],
                [80.0000, 18.0000], [82.0000, 22.0000], [79.0819, 25.0003]
            ]]
        }
    };
    const delhiFIR = {
        type: "Feature", properties: { name: "Delhi FIR" },
        geometry: {
            type: "Polygon", coordinates: [[
                [79.0819, 25.0003], [82.0000, 22.0000], [84.0000, 24.5000], [88.5000, 27.5000],
                [80.0000, 31.0000], [79.0000, 33.0000], [77.0000, 35.5000], [74.0000, 37.0000],
                [72.5000, 34.0000], [70.0000, 30.0000], [70.9167, 25.0000], [79.0819, 25.0003]
            ]]
        }
    };
    const kolkataFIR = {
        type: "Feature", properties: { name: "Kolkata FIR" },
        geometry: {
            type: "Polygon", coordinates: [[
                [82.0000, 22.0000], [85.0000, 18.0000], [89.0000, 16.0000], [92.0000, 12.0000],
                [95.0000, 10.0000], [98.0000, 10.0000], [98.0000, 28.0000], [92.0000, 28.0000],
                [88.5000, 27.5000], [84.0000, 24.5000], [82.0000, 22.0000]
            ]]
        }
    };
    const chennaiFIR = {
        type: "Feature", properties: { name: "Chennai FIR" },
        geometry: {
            type: "Polygon", coordinates: [[
                [82.0000, 22.0000], [80.0000, 18.0000], [77.0000, 17.0000], [74.0000, 15.5000],
                [73.5833, 15.0000], [72.0000, 15.0000], [72.0000, 8.0000], [75.0000, 4.0000],
                [90.0000, 4.0000], [92.0000, 12.0000], [89.0000, 16.0000], [85.0000, 18.0000],
                [82.0000, 22.0000]
            ]]
        }
    };

    function init(stationData, config) {
        stations = stationData;
        console.log("MapCore: Initializing with", stations.length, "stations");

        mapViewport = document.getElementById("map-viewport");
        if (!mapViewport) {
            console.error("MapCore: #map-viewport not found!");
            return;
        }

        mainSvg = d3.select("#main-map");
        insetSvg = d3.select("#inset-map");

        // Live Clock
        setInterval(() => {
            const clockEl = document.getElementById("clock");
            if (clockEl) clockEl.innerText = new Date().toUTCString().split(' ')[4] + " UTC";
        }, 1000);

        setupMap(config);
    }

    async function setupMap(config) {
        const width = mapViewport.clientWidth;
        const height = mapViewport.clientHeight;

        mainProjection = d3.geoMercator()
            .center([76, 18])
            .scale(800)
            .translate([width / 2, height / 2]);

        insetProjection = d3.geoMercator()
            .center([76, 18.5])
            .scale(2800)
            .translate([120, 140]);

        const path = d3.geoPath().projection(mainProjection);
        const insetPath = d3.geoPath().projection(insetProjection);

        try {
            // Use config URL or default
            const url = config?.geojsonUrl || '/static/geojson/india_state.geojson';
            console.log("MapCore: Fetching GeoJSON from", url);
            
            const response = await fetch(url);
            if (!response.ok) throw new Error(`GeoJSON fetch failed ${response.status}`);
            geoData = await response.json();

            // Zoom Layer
            zoomLayer = mainSvg.append("g").attr("id", "zoom-container");

            // Setup Zoom
            const zoom = d3.zoom()
                .scaleExtent([0.5, 8])
                .on("zoom", (event) => {
                    requestAnimationFrame(() => {
                        zoomLayer.attr("transform", event.transform);
                        updateScaleBar(event.transform.k, width, height);
                    });
                });
            mainSvg.call(zoom);

            // Render Maps
            renderLayer(zoomLayer, mainProjection, path, false);
            const insetGroup = insetSvg.append("g");
            renderLayer(insetGroup, insetProjection, insetPath, true);

            updateScaleBar(1, width, height);

            // Setup Controls
            d3.select("#zoom-in").on("click", () => mainSvg.transition().call(zoom.scaleBy, 1.5));
            d3.select("#zoom-out").on("click", () => mainSvg.transition().call(zoom.scaleBy, 0.6));
            d3.select("#zoom-reset").on("click", () => mainSvg.transition().call(zoom.transform, d3.zoomIdentity));

        } catch (error) {
            console.error("Map Setup Failed:", error);
            alert("Map Error: " + error.message);
        }
    }

    function renderLayer(target, projection, geoPath, isInset) {
        // States
        target.append("g")
            .selectAll("path")
            .data(geoData.features)
            .enter().append("path")
            .attr("d", geoPath)
            .attr("class", "state-color muted");

        // FIRs (Main Only)
        if (!isInset) {
            const firs = [
                { data: mumbaiFIR, class: "fir-mumbai" },
                { data: delhiFIR, class: "fir-delhi" },
                { data: kolkataFIR, class: "fir-kolkata" },
                { data: chennaiFIR, class: "fir-chennai" }
            ];
            firs.forEach(fir => {
                target.append("path")
                    .datum(fir.data)
                    .attr("d", geoPath)
                    .attr("class", `fir-boundary ${fir.class}`);
            });
        }

        // Labels
        target.append("g").attr("class", "state-label-group")
            .selectAll("text")
            .data(geoData.features)
            .enter().append("text")
            .attr("class", "state-map-label muted")
            .attr("transform", d => {
                const c = projection(d3.geoCentroid(d));
                return c ? `translate(${c[0]}, ${c[1]})` : null;
            })
            .attr("text-anchor", "middle")
            .attr("font-size", isInset ? "12px" : "8px")
            .text(d => d.properties.NAME_1 || d.properties.st_nm || d.properties.NAME);

        // Graticule
        target.append("path")
            .datum(d3.geoGraticule().step([5, 5]))
            .attr("class", "graticule")
            .attr("d", geoPath);

        // Pins
        const pinGroup = target.append("g");
        const dropletPath = "M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7z";

        stations.forEach(a => {
            const coords = projection([a.long, a.lat]);
            if (!coords) return;

            const pin = pinGroup.append("g")
                .datum(a)
                .attr("class", `airport-pin ${a.icao === 'VABB' ? 'hub' : ''}`)
                .attr("id", `pin-${a.icao}-${isInset ? 'inset' : 'main'}`)
                .attr("transform", `translate(${coords[0]}, ${coords[1]}) scale(${isInset ? 1.2 : 0.8})`)
                .on("click", (event) => {
                    event.stopPropagation();
                    fireEvent('airport-selected', a);
                })
                .on("dblclick", (event) => {
                    event.stopPropagation();
                    fireEvent('view-dashboard', a);
                });

            const pinBody = pin.append("g").attr("class", "pin-body");
            pinBody.append("circle").attr("class", "sonar").attr("cx", 0).attr("cy", -13).attr("r", 0);
            pinBody.append("path")
                .attr("class", "droplet-path")
                .attr("d", dropletPath)
                .attr("transform", "translate(-12, -22)");
            pinBody.append("circle")
                .attr("class", "pin-center")
                .attr("cx", 0).attr("cy", -13).attr("r", 3);

            pin.append("text")
                .attr("class", "airport-label")
                .attr("dx", 0).attr("dy", -28)
                .attr("text-anchor", "middle")
                .text(isInset ? a.name : a.icao);
        });

        // Populate Sidebar (Since we're here, let's trigger it or let Adapter handle it? 
        // Adapter uses MapCore only for MAP stuff. The sidebar is HTML. 
        // Let's populate Sidebar here since we have the data loop, 
        // OR better: dispatch an event that data is loaded and let Adapter populate sidebar?
        // For simplicity, let's do it here as it was in original script, but using data.)

        const sidebarList = d3.select("#airport-nav-list");
        if (!sidebarList.empty()) {
            sidebarList.html(""); // Clear
            stations.forEach(a => {
                const li = sidebarList.append("li")
                    .attr("data-icao", a.icao)
                    .on("click", () => {
                        highlight(a.icao);
                        // Event bubbling will be caught by Adapter listener too, 
                        // but highlighting is visual.
                    });
                li.html(`<span class="nav-name">${a.name}</span><span class="nav-code">${a.icao}</span>`);
            });
        }
    }

    function updateScaleBar(k, width, height) {
        const center = mainProjection.invert([width / 2, height / 2]);
        const p1 = mainProjection.invert([width / 2, height / 2]);
        const p2 = mainProjection.invert([width / 2 + 100 / k, height / 2]); // 100 screen px

        if (p1 && p2) {
            // Distance Calculation (Haversine approx)
            const R = 6371;
            const dLat = (p2[1] - p1[1]) * Math.PI / 180;
            const dLon = (p2[0] - p1[0]) * Math.PI / 180;
            const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
                Math.cos(p1[1] * Math.PI / 180) * Math.cos(p2[1] * Math.PI / 180) *
                Math.sin(dLon / 2) * Math.sin(dLon / 2);
            const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
            const kmPer100Px = R * c;

            // Logic to snap to nice numbers
            const niceNumbers = [10, 20, 50, 100, 200, 500, 1000, 2000];
            let displayKm = 500, displayPx = 100;

            for (let num of niceNumbers) {
                const px = (100 * num) / kmPer100Px;
                if (px >= 60 && px <= 180) {
                    displayKm = num;
                    displayPx = px;
                    break;
                }
            }

            const line = document.getElementById("scale-bar-line");
            const text = document.getElementById("scale-bar-text");
            if (line && text) {
                line.style.width = `${displayPx}px`;
                text.innerText = `${displayKm} km`;
            }
        }
    }

    function highlight(icao) {
        // Remove active class from all
        d3.selectAll(".airport-pin").classed("active", false);
        d3.selectAll("#airport-nav-list li").classed("active", false);

        // Add to selected
        const pins = d3.selectAll(`#pin-${icao}-main, #pin-${icao}-inset`);
        pins.classed("active", true);

        // Highlight sidebar
        d3.select(`#airport-nav-list li[data-icao='${icao}']`).classed("active", true);

        // Fire event so Adapter can update info panel
        // (If called from map click, event fires there. If called from sidebar, we fire here)
        // Find data
        const station = stations.find(s => s.icao === icao);
        if (station) {
            fireEvent('airport-selected', station);
        }
    }

    function fireEvent(name, detail) {
        const event = new CustomEvent(name, { detail: detail });
        document.dispatchEvent(event);
    }

    return {
        init: init,
        highlight: highlight
    };

})();