
window.MapAdapter = {
    init: function () {
        console.log("Map Adapter: Initializing...");

        const stationData = window.stationData;
        if (!stationData) {
            console.error("Map Adapter: Critical - window.stationData is missing!");
            return;
        }

        console.log(`Map Adapter: Loaded ${stationData.stations.length} stations.`);

        if (window.MapCore && typeof window.MapCore.init === 'function') {
            window.MapCore.init(stationData.stations, {
                useFirBoundaries: true,
                geojsonUrl: stationData.config?.geojsonUrl
            });
        } else {
            console.error("Map Adapter: MapCore not found. Ensure map_new.js is loaded.");
            return;
        }

        this.setupEvents();

        this.startPolling();
    },

    setupEvents: function () {
        document.addEventListener('airport-selected', (e) => {
            const airport = e.detail;
            console.log("Map Adapter: Selected", airport.icao);
            this.updateInfoPanel(airport);
        });

        document.addEventListener('view-dashboard', (e) => {
            const icao = e.detail.icao;
            if (icao) {
                window.location.href = `/dashboard/${icao}`;
            }
        });

        const sidebarList = document.getElementById('airport-nav-list');
        if (sidebarList) {
            sidebarList.addEventListener('click', (e) => {
                const li = e.target.closest('li');
                if (li && li.dataset.icao) {
                    const icao = li.dataset.icao;
                    window.MapCore.highlight(icao);
                }
            });
        }
    },

    updateInfoPanel: function (airport) {
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

        set('det-wind', airport.wind || '--');
        set('det-vis', airport.vis || '--');

        if (airport.raw_metar) {
            set('det-metar', airport.raw_metar);
        } else {
            set('det-metar', `METAR ${airport.icao} ... (Live data fetch pending)`);
            this.fetchMetar(airport.icao);
        }
    },

    fetchMetar: function (icao) {
    },

    startPolling: function () {
        setInterval(() => {
        }, 30000);
    }
};

document.addEventListener('DOMContentLoaded', () => {
    window.MapAdapter.init();
});
