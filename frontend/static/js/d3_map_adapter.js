
(function () {
    'use strict';

    document.addEventListener('DOMContentLoaded', function () {
        console.log('D3 Map Adapter: Initializing...');

        const stationCoords = window.IMD_STATION_COORDS || {};
        const stationNames = window.IMD_STATION_NAMES || {};

        const airportData = Object.entries(stationCoords).map(([code, coords]) => ({
            name: stationNames[code] || code,
            code: code,
            lat: coords[0],
            long: coords[1]
        }));

        console.log(`D3 Map Adapter: Loaded ${airportData.length} airports`);

        if (window.D3MapCore && typeof window.D3MapCore.init === 'function') {
            window.D3MapCore.init('#d3-map-svg', airportData, {
                geojsonUrl: window.IMD_GEOJSON_URL || '/static/geojson/india_state.geojson',
                showFIR: true,

                onAirportClick: function (airport) {
                    console.log('Airport selected:', airport.code);
                    window.location.href = `/dashboard/${airport.code}`;
                },

                onError: function (error) {
                    console.error('Map initialization failed:', error);
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
