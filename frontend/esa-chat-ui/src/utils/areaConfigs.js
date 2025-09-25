import { fromLonLat } from "ol/proj"

export const areaConfigs = {
    PILOT_THESSALONIKI: {
        center: fromLonLat([
            (21.95 + 22.52) / 2, // lon center
            (40.55 + 40.94) / 2  // lat center
        ]),
        zoom: 9.9,
        shapefile: "Land_Suitability:PILOT_THESSALONIKI"
    },
    PILOT_PILSEN: {
        center: fromLonLat([
            (12.45 + 13.55) / 2,
            (49.35 + 50.15) / 2
        ]),
        zoom: 8.8,
        shapefile: "Land_Suitability:PILOT_PILSEN"
    },
    PILOT_OLOMOUC: {
        center: fromLonLat([
            (16.55 + 18.05) / 2,
            (49.26 + 50.55) / 2
        ]),
        zoom: 8.1,
        shapefile: "Land_Suitability:PILOT_OLOMOUC"
    },
    GREECE: {
        center: fromLonLat([
            (18.95 + 29.05) / 2,
            (33.95 + 43.05) / 2
        ]),
        zoom: 6,
        shapefile: ""
    },
    CZECHIA: {
        center: fromLonLat([
            (10.95 + 19.05) / 2,
            (47.95 + 52.05) / 2
        ]),
        zoom: 6.5,
        shapefile: ""
    },
};