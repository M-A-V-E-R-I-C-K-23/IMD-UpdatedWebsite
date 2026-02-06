const highlightStates = ["maharashtra", "goa"];

// Core Map Logic
document.addEventListener("DOMContentLoaded", async () => {
    const mainSvg = d3.select("#main-map");
    const insetSvg = d3.select("#inset-map");

    // Dimensions from Container
    const container = document.getElementById("map-viewport");
    if (!container) return;

    const width = container.clientWidth;
    const height = container.clientHeight;

    // Projections
    // Adjusted center for generic view, tweak as needed
    const mainProjection = d3.geoMercator()
        .center([82, 22])
        .scale(1200)
        .translate([width / 2, height / 2]);

    const insetProjection = d3.geoMercator()
        .center([76, 18.5])
        .scale(2800)
        .translate([120, 140]);

    const path = d3.geoPath().projection(mainProjection);
    const insetPath = d3.geoPath().projection(insetProjection);

    // Zoom Setup
    const zoomLayer = mainSvg.append("g").attr("id", "zoom-container");
    const zoom = d3.zoom()
        .scaleExtent([0.5, 8])
        .on("zoom", (event) => {
            zoomLayer.attr("transform", event.transform);
        });

    mainSvg.call(zoom);

    // Render Function
    const renderMap = (targetGroup, projection, geoPath, geoData, isInset = false) => {
        const group = targetGroup.append("g");

        // States
        group.selectAll(".state-color")
            .data(geoData.features)
            .enter()
            .append("path")
            .attr("d", geoPath)
            .attr("class", d => {
                const name = (d.properties.NAME_1 || d.properties.st_nm || d.properties.NAME || "").toLowerCase();
                const highlight = highlightStates.includes(name);
                return `state-color ${highlight ? 'highlighted' : 'muted'}`;
            });

        // Labels
        const labelGroup = targetGroup.append("g").attr("class", "state-label-group");
        labelGroup.selectAll(".state-map-label")
            .data(geoData.features)
            .enter()
            .append("text")
            .attr("class", d => {
                const name = (d.properties.NAME_1 || d.properties.st_nm || d.properties.NAME || "").toLowerCase();
                const highlight = highlightStates.includes(name);
                return `state-map-label ${highlight ? 'highlighted' : 'muted'}`;
            })
            .attr("transform", d => {
                const centroid = projection(d3.geoCentroid(d));
                return centroid ? `translate(${centroid[0]}, ${centroid[1]})` : null;
            })
            .attr("text-anchor", "middle")
            .attr("font-size", isInset ? "12px" : "10px")
            .text(d => d.properties.NAME_1 || d.properties.st_nm || d.properties.NAME);

        // Graticule
        const graticule = d3.geoGraticule().step([5, 5]);
        targetGroup.append("path")
            .datum(graticule)
            .attr("class", "graticule")
            .attr("d", geoPath);

        // PINS RENDER LOGIC (Static for now, no sidebar interaction)
        // Check if `stations` variable exists (passed from HTML/Flask)
        if (typeof stationCoords !== 'undefined') {
            const pinGroup = targetGroup.append("g");
            const dropletPath = "M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7z";

            Object.entries(stationCoords).forEach(([code, coords]) => {
                // coords is [lat, lon], but projection takes [lon, lat]
                const projCoords = projection([coords[1], coords[0]]);
                if (!projCoords) return;

                const pin = pinGroup.append("g")
                    .attr("class", `airport-pin ${code === 'VABB' ? 'hub' : ''}`)
                    .attr("transform", `translate(${projCoords[0]}, ${projCoords[1]}) scale(${isInset ? 1.2 : 0.8})`);

                const pinBody = pin.append("g").attr("class", "pin-body");
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
                    .text(code);
            });
        }
    };

    // Load Data
    try {
        // Use local GeoJSON if available, else fetch
        const response = await fetch("/static/geojson/india_state.geojson");
        const geoData = await response.json();

        // Main Map Render (to zoom layer)
        renderMap(zoomLayer, mainProjection, path, geoData);

        // Inset Map Render (to svg directly)
        const insetGroup = insetSvg.append("g");
        renderMap(insetGroup, insetProjection, insetPath, geoData, true);

    } catch (err) {
        console.error("Map Load Error:", err);
    }

    // Controls
    d3.select("#zoom-in").on("click", () => mainSvg.transition().duration(400).call(zoom.scaleBy, 1.5));
    d3.select("#zoom-out").on("click", () => mainSvg.transition().duration(400).call(zoom.scaleBy, 0.6));
    d3.select("#zoom-reset").on("click", () => mainSvg.transition().duration(750).call(zoom.transform, d3.zoomIdentity));
});
