/**
 * Map Adapter
 * Bridges the D3 Map implementation (map_new.js) with the Flask Backend and existing Dashboard Logic.
 */

window.MapAdapter = {
    init: function () {
        console.log("Map Adapter: Initializing...");

        // 1. Read Data Inject from Flask
        const stationData = window.stationData;
        if (!stationData) {
            console.error("Map Adapter: Critical - window.stationData is missing!");
            return;
        }

        console.log(`Map Adapter: Loaded ${stationData.stations.length} stations.`);

        // 2. Initialize Map Core (D3 Logic)
        // Ensure MapCore exists (defined in map_new.js)
        if (window.MapCore && typeof window.MapCore.init === 'function') {
            window.MapCore.init(stationData.stations, {
                // Config
                useFirBoundaries: true,
                geojsonUrl: stationData.config?.geojsonUrl
            });
        } else {
            console.error("Map Adapter: MapCore not found. Ensure map_new.js is loaded.");
            return;
        }

        // 3. Setup Event Listeners
        this.setupEvents();

        // 4. Start Polling for Alerts/SIGMETs
        this.startPolling();
    },

    setupEvents: function () {
        // Event: Airport Selected on Map
        document.addEventListener('airport-selected', (e) => {
            const airport = e.detail;
            console.log("Map Adapter: Selected", airport.icao);
            this.updateInfoPanel(airport);
        });

        // Event: View Dashboard Request (Double Click or Button)
        document.addEventListener('view-dashboard', (e) => {
            const icao = e.detail.icao;
            if (icao) {
                window.location.href = `/dashboard/${icao}`;
            }
        });

        // Event: Sidebar Navigation Click
        const sidebarList = document.getElementById('airport-nav-list');
        if (sidebarList) {
            sidebarList.addEventListener('click', (e) => {
                // Delegate click to list item
                const li = e.target.closest('li');
                if (li && li.dataset.icao) {
                    const icao = li.dataset.icao;
                    window.MapCore.highlight(icao);

                    // Also update info panel manually if needed, 
                    // though MapCore.highlight should probably trigger 'airport-selected' too? 
                    // Let's assume MapCore.highlight dispatches the event or we do it here.
                    // For now, let's rely on MapCore firing the event back.
                }
            });
        }
    },

    updateInfoPanel: function (airport) {
        // Update DOM elements in the Right Panel
        const set = (id, val) => {
            const el = document.getElementById(id);
            if (el) el.textContent = val;
        };
        const show = (id) => {
            const el = document.getElementById(id);
            if (el) el.classList.remove('hidden');
        };
        const hide = (id) => {
            const el = document.getElementById(id);
            if (el) el.classList.add('hidden');
        };

        hide('no-selection-msg');
        show('airport-details');

        set('det-name', airport.name);
        set('det-code', airport.icao);

        // These might come from live data later, for now use what we have in stationData
        // or fetch live METAR?
        // The stationData injected from flask might have 'wind' and 'vis' if we included it.
        // If not, we might need to fetch it. 
        // For the static prototype, let's use the object properties.
        set('det-wind', airport.wind || '--');
        set('det-vis', airport.vis || '--');

        // Update METAR Text if available
        if (airport.raw_metar) {
            set('det-metar', airport.raw_metar);
        } else {
            // Generate a placeholder or fetch
            set('det-metar', `METAR ${airport.icao} ... (Live data fetch pending)`);
            // Trigger a fetch?
            this.fetchMetar(airport.icao);
        }
    },

    fetchMetar: function (icao) {
        // TODO: Implement fetch from /api/data?station=ICAO
        // This is a "nice to have" for the bridge.
    },

    startPolling: function () {
        // Poll for Active Warnings (every 30s)
        setInterval(() => {
            // fetch('/alerts/map')... 
            // window.MapCore.updateAlerts(data)...
        }, 30000);
    }
};

// Auto-init on DOM Ready
document.addEventListener('DOMContentLoaded', () => {
    window.MapAdapter.init();
});
