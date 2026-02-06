/**
 * D3 Map Adapter
 * Bridges Flask template data with D3MapCore
 * Preserves existing IMD dashboard event handlers
 */

(function () {
    'use strict';

    // Wait for DOM and D3MapCore to be ready
    document.addEventListener('DOMContentLoaded', function () {
        console.log('D3 Map Adapter: Initializing...');

        // Get station data from Flask template (injected via Jinja)
        const stationCoords = window.IMD_STATION_COORDS || {};
        const stationNames = window.IMD_STATION_NAMES || {};

        // Transform to D3MapCore format
        const airportData = Object.entries(stationCoords).map(([code, coords]) => ({
            name: stationNames[code] || code,
            code: code,
            lat: coords[0],
            long: coords[1]
        }));

        console.log(`D3 Map Adapter: Loaded ${airportData.length} airports`);

        // Initialize D3 map
        if (window.D3MapCore && typeof window.D3MapCore.init === 'function') {
            window.D3MapCore.init('#d3-map-svg', airportData, {
                geojsonUrl: window.IMD_GEOJSON_URL || '/static/geojson/india_state.geojson',
                showFIR: true,

                // Event handler: preserve existing navigation behavior
                onAirportClick: function (airport) {
                    console.log('Airport selected:', airport.code);
                    // Navigate to dashboard (existing IMD behavior)
                    window.location.href = `/dashboard/${airport.code}`;
                },

                // Error handler
                onError: function (error) {
                    console.error('Map initialization failed:', error);
                    // Optionally show user-friendly error message
                    const mapContainer = document.querySelector('.map-wrapper');
                    if (mapContainer) {
                        mapContainer.innerHTML = `
                            <div style="display: flex; align-items: center; justify-content: center; height: 100%; color: #666;">
                                <div style="text-align: center;">
                                    <p style="font-size: 1.2em; margin-bottom: 10px;">⚠️ Map Loading Failed</p>
                                    <p style="font-size: 0.9em;">Please refresh the page or contact support</p>
                                </div>
                            </div>
                        `;
                    }
                }
            });
        } else {
            console.error('D3 Map Adapter: D3MapCore not found!');
        }
    });
})();
