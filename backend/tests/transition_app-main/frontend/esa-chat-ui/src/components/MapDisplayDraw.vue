<template>
    <div class="flex flex-col max-w-[75%] items-start map-wrapper">
    <!-- <div class="map-wrapper"> -->
        <div id="map" class="map-container"></div>

        <div class="controls" v-if="!hasData">
            <button 
                type="button"
                class="bg-emerald-500 hover:bg-emerald-600 disabled:opacity-50 disabled:cursor-not-allowed" 
                @click="clearLastPolygon" 
                :disabled="!hasPolygons"
            >
                Clear Last Polygon
            </button>
            <button 
                type="button"
                class="bg-emerald-500 hover:bg-emerald-600 disabled:opacity-50 disabled:cursor-not-allowed" 
                @click="clearAllPolygons" 
                :disabled="!hasPolygons"
            >
                Clear All Polygons
            </button>
        </div>
    </div>
</template>
    
<script setup>
    import "ol/ol.css" // OpenLayers default styles

    import { Map, View, TileLayer, VectorLayer, VectorSource, ImageLayer, ImageWMS, GeoJSON, XYZ } from '../utils/mapUtils'
    import Draw from "ol/interaction/Draw"
    import Modify from "ol/interaction/Modify"

    import { ref, onMounted, watch } from 'vue'
    import { areaConfigs } from "../utils/areaConfigs"
  

    const map = ref(null)
    const vectorLayer =  ref(null)
    const vectorSource = ref(new VectorSource()) // Source for vector data
    const drawInteraction = ref(null)
    const modifyInteraction = ref(null)
    const baseWmsUrl = import.meta.env.VITE_WMS_BASE_URL

    const hasPolygons = ref(false)
    const hasData =  ref(false)
   
    const props = defineProps({
        pilotArea: {
            type: String,
            default: null
        }
    })

    const emit = defineEmits([
        'geojson-input',
    ])

    onMounted(() => {
        initializeMap()
        vectorSource.value.clear()
        enableDrawing()  // Enable drawing only if no initial data
        updatePolygonState()
    })

    watch(() => props.pilotArea, (newArea) => {
        const config = areaConfigs[newArea]
        if (map.value && config) {
            map.value.getView().setCenter(config.center)
            map.value.getView().setZoom(config.zoom)

            // Add pilot boundary shapefile layer
            if (config.shapefile) {
                addShapefileLayer(config.shapefile)
            }
        }
    })

    const initializeMap = () => {
        const areaConfig = areaConfigs[props.pilotArea] || areaConfigs[PILOT_THESSALONIKI]

        // Base layer - ArcGIS Satellite Imagery
        const satelliteLayer = new TileLayer({
            source: new XYZ({
                url: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
                attributions: "&copy; <a href='https://www.esri.com/'>Esri</a> contributors",
            }),
        })

        // Vector source and layer for drawing and editing
        vectorLayer.value = new VectorLayer({
            source: vectorSource.value,
        })

        // Ensure the vector layer is always initialized here
        vectorSource.value = vectorLayer.value.getSource()

        // Watch for changes in the vector source
        vectorSource.value.on("addfeature", updatePolygonState)
        vectorSource.value.on("removefeature", updatePolygonState)
        vectorSource.value.on("clear", updatePolygonState)

        // Initialize the map
        map.value = new Map({
            target: "map",
            layers: [satelliteLayer, vectorLayer.value],
            view: new View({
                center: areaConfig.center,
                zoom: areaConfig.zoom,
            }),
        })

        // Add pilot boundary shapefile layer
        if (areaConfig.shapefile) {
            addShapefileLayer(areaConfig.shapefile)
        }
    }

    const enableDrawing = () => {
        // Add draw interaction
        drawInteraction.value = new Draw({
            source: vectorSource.value,
            type: "Polygon",
        })
        map.value.addInteraction(drawInteraction.value)

        // Enable modifying drawn polygons
        modifyInteraction.value = new Modify({
            source: vectorSource.value,
        })
        map.value.addInteraction(modifyInteraction.value)

        // Show GeoJSON popup on polygon creation
        drawInteraction.value.on("drawend", () => {
            setTimeout(() => {
                const geojson = exportGeoJson()
                emit("geojson-input", JSON.stringify(geojson, null, 2)) // send to input bar
            }, 0)
        })

        // Update GeoJSON popup after modifying polygons
        modifyInteraction.value.on("modifyend", () => {
            const geojson = exportGeoJson()
            emit("geojson-input", JSON.stringify(geojson, null, 2)) // send to input bar
        })
    }


    const addShapefileLayer = (layerName) => {
        if (!layerName || !map.value) return

        const boundaryLayer = new ImageLayer({
            source: new ImageWMS({
                url: baseWmsUrl,
                params: {
                    LAYERS: layerName,
                    TILED: true,
                    FORMAT: "image/png",
                    TRANSPARENT: true,
                },
                serverType: "geoserver",
                crossOrigin: "anonymous",
            }),
            opacity: 0.3,
        })

        map.value.addLayer(boundaryLayer)
    }

    const exportGeoJson = () => {
        // Export vector layer features as GeoJSON
        const geojsonFormat = new GeoJSON()
        const features = vectorSource.value.getFeatures()
        const geojson = geojsonFormat.writeFeatures(features, {
            featureProjection: "EPSG:3857", // Projection for OpenLayers
        });
        return JSON.parse(geojson) // Return parsed JSON
    }

    
    const updatePolygonState = () => {
        // Update `hasPolygons` to reflect the presence of polygons
        hasPolygons.value = (vectorSource.value?.getFeatures()?.length || 0) > 0
    }

    const clearLastPolygon = () => {
        const features = vectorSource.value.getFeatures()
        if (features.length > 0) {
            vectorSource.value.removeFeature(features[features.length - 1])
            // Emit updated GeoJSON (or empty if none left)
            const count = vectorSource.value.getFeatures().length
            emit("geojson-input", count ? JSON.stringify(exportGeoJson(), null, 2) : "")
        }
    }

    const clearAllPolygons = () => {
        vectorSource.value.clear()
        emit("geojson-input", '') // send to input bar
    }
</script>
  
  <style scoped>
    .map-wrapper {
        margin-top: 10px;
        margin-left: 43px;
    }
    #map {
      width: 100%; /* Full width */
      height: 450px;
      box-sizing: border-box; /* Include padding and border in the width calculation */
      background-color: transparent !important; 
      margin-top: 10px;
      padding: 0;
    }
  
    .map-container {
      width: 100%;
      height: 450px; /* Fixed height */
      box-sizing: border-box;
      border: 1px solid #ccc;
      border-radius: 4px;
      box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1); /* Subtle shadow */
      background-color: #f0f0f0;
      margin: 0;
      padding: 0;
    }

    .controls {
      display: flex;
      gap: 10px;
      margin-top: 10px;
    }
    button {
      padding: 5px 10px;
      color: white;
      border: none;
      cursor: pointer;
      border-radius: 4px;
      font-size: 14px;
    }

  </style>
    