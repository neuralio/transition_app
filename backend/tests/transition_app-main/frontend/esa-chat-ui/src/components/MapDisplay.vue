<template>
    <div class="map-wrapper">
        <div id="map-popup" class="map-popup" ref="popupRef"></div>
        <div :id="mapId" class="map-container"></div>

        <div class="legend-container" v-if="legends.length > 0">
            <div class="legend-item">
                <div class="legend-label">
                    <div v-for="legend in legends" :key="legend.layerName" class="legend-item">
                        <div class="legend-label">{{ legend.layerTitle }}</div>
                    </div>
                </div>
                <img
                    :src="legends[0].url"
                    alt="Combined legend for all layers"
                    class="legend-image"
                />
            </div>
        </div>

        <div class="opacity-controls" v-if="layerWMS.length > 0">
            <div
                v-for="(entry, index) in layerWMS"
                    :key="entry.layerName"
                    class="opacity-slider"
            >
                <label :for="`opacity-${index}`">{{ entry.layerTitle }} </label><br>
                <div class="inner-controls">
                    <span>Opacity</span>
                    <input
                        type="range"
                        :id="`opacity-${index}`"
                        min="0"
                        max="1"
                        step="0.01"
                        v-model.number="entry.opacity"
                        @input="entry.layer.setOpacity(entry.opacity)"
                        :style="sliderStyle(index, entry.opacity)"
                    />
                    <span>{{ (entry.opacity * 100).toFixed(0) }}%</span>
                </div>
            </div>
        </div>

        <div class="flex flex-col max-w-[100%] items-start bottom-explanation" v-if="mapExplanation">
            <div
                class="relative p-3 rounded-lg text-sm bg-gray-200 dark:bg-gray-700 dark:text-white text-gray-900 rounded-bl-none"
                v-html="mapExplanation"
                style="line-height: 1.4;"
            ></div>
        </div>
    </div>
</template>
    
<script setup>
    import "ol/ol.css" // OpenLayers default styles

    import { Map, View, TileLayer, VectorLayer, VectorSource, ImageLayer, ImageWMS, GeoJSON, XYZ } from '../utils/mapUtils'
    import Draw from "ol/interaction/Draw"
    import Modify from "ol/interaction/Modify"
    import { fromLonLat, toLonLat } from "ol/proj"
    import { getVectorContext } from 'ol/render'
    import { Point } from 'ol/geom'
    import { Feature } from 'ol'
    import { Fill, Style, Icon } from 'ol/style'
  
    import gs from '../geoserver'
    import { ref, onMounted, watch, nextTick } from 'vue'
    import { areaConfigs } from "../utils/areaConfigs"
  

    const map = ref(null)
    const popupRef = ref(null)
    const vectorLayer =  ref(null)
    const vectorSource = ref(new VectorSource()) // Source for vector data
    const drawInteraction = ref(null)
    const modifyInteraction = ref(null)
    const markerSource = ref(new VectorSource())
    const markerLayer = ref(new VectorLayer({
        source: markerSource.value,
        style: new Style({
            image: new Icon({
                anchor: [0.5, 1],
                src: 'https://cdn-icons-png.flaticon.com/512/64/64113.png',
                scale: 0.05,
                opacity: 1,
            })
        }),
        zIndex: 1000
    }))

    const hasPolygons = ref(false)
    const hasData =  ref(false)
    const layerWMS = ref([])
    const wmsReady = ref(false)
    const baseWmsUrl = import.meta.env.VITE_WMS_BASE_URL
    const availableDates = ref([])
    const legends = ref([]) // Store legend URLs and their corresponding layer names
    const xmlDoc = ref(null)

    const palette = [ "#009688", "#f5fa93", "#d64bde", "#4ba3de", "#f76a6a", "#9e9e9e", "#744bde", "#4bde80", "#607d8b", "#4bded7", "#4b67de" ]
      
    const props = defineProps({
        pilotArea: {
            type: String,
            default: null
        },
        geoJsonData: {
            type: Object,
            default: null,
        },
        selectedDate: {
            type: String,
            default: null,
        },
        wmsLayers: {
            type: Array,
            default: []
        },
        triggerWmsClick: {
            type: Boolean,
            default: false
        },
        mapId: {
            type: String,
            required: true
        },
        mapExplanation: {
            type: String,
            default: null,
        }
    })

    const emit = defineEmits([
        'update-graph', 
        'dates-available', 
        'geojson-input',
        'trigger-wms-click-handled'
    ])


    onMounted(() => {
        initializeMap()

        if (props.geoJsonData && props.geoJsonData.features?.length > 0) {
            loadGeoJsonData(props.geoJsonData)
            hasData.value = true  // Disable draw/edit and hide buttons

            if (Array.isArray(props.wmsLayers) && props.wmsLayers.length > 0) 
                addWmsLayers(props.wmsLayers)

        } else {
            vectorSource.value.clear()
            layerWMS.value = []
            xmlDoc.value = null

            enableDrawing()  // Enable drawing only if no initial data
        }
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


    watch(() => props.selectedDate, (newDate) => {
        if (!map.value) {
            console.warn("Map is not initialized yet, skipping date update.")
            return
        }

        if (newDate) {
            updateWMSLayers(newDate)

            // Apply the GeoJSON extent to WMS layers
            const features = new GeoJSON().readFeatures(props.geoJsonData, {
                featureProjection: "EPSG:3857", // Ensure projection matches the map
            });
            vectorSource.value.clear()
            vectorSource.value.addFeatures(features); // Add GeoJSON features to the vector source

            applyExtentToWmsLayers() // Update WMS layers with the GeoJSON extent
        }    
    })

    watch(() => props.geoJsonData, (newGeoJson) => {
        if (!newGeoJson) {
            console.warn("No GeoJSON data provided for cropping")

            try {
                vectorSource.value.clear()
                layerWMS.value = []
                xmlDoc.value = null
            } catch (error) {
                console.error("Unexpected error:", error)
            }
        } else {
            // Parse the GeoJSON data
            const features = new GeoJSON().readFeatures(newGeoJson, {
                featureProjection: 'EPSG:3857', // Ensure the projection matches your map
            });

            vectorSource.value.clear()
            vectorSource.value.addFeatures(features)

            // Apply the new extent to the WMS layers
            applyExtentToWmsLayers()
        }

    })

    watch(
        () => layerWMS.value.length,
        (newLength) => {
            const expected = props.wmsLayers?.length || 0
            if (newLength === expected && expected > 0) {
                console.log("✅ WMS layers fully loaded")
                wmsReady.value = true

                // Apply the GeoJSON extent to WMS layers
                const features = new GeoJSON().readFeatures(props.geoJsonData, {
                    featureProjection: "EPSG:3857", // Ensure projection matches the map
                })
                vectorSource.value.clear()
                vectorSource.value.addFeatures(features) // Add GeoJSON features to the vector source
                applyExtentToWmsLayers()

                enableWMSClickQuery() // Enable WMS click interaction
            }
        }
    )

    watch(
        [() => props.triggerWmsClick, wmsReady],
        async ([clickTrigger, ready]) => {
            if (clickTrigger && ready) {
                await nextTick()
                simulateClickFromGeoJson()
                emit('trigger-wms-click-handled')
            } else {
                console.log("⏳ Waiting — trigger:", clickTrigger, "WMS ready:", ready)
            }
        }
    )


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

        // Initialize the map
        map.value = new Map({
            target: props.mapId,
            layers: [satelliteLayer, vectorLayer.value, markerLayer.value],
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


    const addWmsLayers = async (layerNames) => {
        if (!Array.isArray(availableDates.value)) {
            availableDates.value = []
        }

        if (xmlDoc.value == null)
            await callGetCapabilities()  

        if (xmlDoc.value) {
            for (const layerName of layerNames) {
                const timeSteps = fetchTimeSteps(layerName, xmlDoc.value)
                if (timeSteps.length > 0) {
                    // Emit available dates only once
                    if (availableDates.value.length === 0) {
                        availableDates.value = timeSteps
                        emit("dates-available", timeSteps)
                    }

                    // Add WMS layer using the first available date
                    addLayerToMap(layerName, timeSteps[0])
                } else {
                    console.warn(`No time steps available for layer: ${layerName}`)
                }
            }
        }    

        // Ensure the vector layer (initialData) is added last
        map.value.addLayer(new VectorLayer({ source: vectorSource.value }))
    }

    const addLayerToMap = (layerName, time) => {
        const layer = new ImageLayer({
            opacity: 0.5,
            source: new ImageWMS({
                url: baseWmsUrl,
                params: {
                    LAYERS: layerName,
                    TIME: time,
                    TILED: true,
                    FORMAT: "image/png", // Ensure transparency
                    TRANSPARENT: true,
                },
                ratio: 1,
                serverType: "geoserver",
                crossOrigin: "anonymous",
            }),
        })

        const layerTtl = fetchLayerTitle(layerName, xmlDoc.value)
        layerWMS.value.push({ layerName, layer, opacity: 0.5, layerTitle: layerTtl });
        map.value.addLayer(layer);
        
        // Fetch the legend URL for this layer
        const legendUrl = `${baseWmsUrl}?REQUEST=GetLegendGraphic&VERSION=1.3.0&FORMAT=image/png&LAYER=${layerName}`
        legends.value.push({ url: legendUrl, layerName: layerName, layerTitle: layerTtl })
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


    const getVectorLayerExtent = () => {
        if (!vectorSource.value || vectorSource.value.getFeatures().length === 0) {
            console.warn("No features in vector source.")
            return null
        }

        // Calculate extent of all features in the vectorSource
        return vectorSource.value.getExtent()
    }

    const applyExtentToWmsLayers = () => {
        const extent = getVectorLayerExtent()
        if (!extent) {
            console.warn("No extent available to apply.")
            return
        }

        // Apply the extent to all WMS layers
        layerWMS.value.forEach(({ layer }) => {
            layer.setExtent(extent)
            layer.getSource().refresh()
        })

        map.value.render()
    }


    const clipLayer = (layer) => {
        layer.on("postrender", (e) => {
          const ctx = e.context // The canvas context
          const vectorContext = getVectorContext(e)

          // Save the original state of the canvas context
          ctx.save()

          // Parse GeoJSON features to draw the clipping area
          const features = new GeoJSON().readFeatures(props.geoJsonData, {
            featureProjection: "EPSG:3857", // Match the map projection
          })

          // Change the blending mode to clip only the desired area
          ctx.globalCompositeOperation = "destination-in"
          const style = new Style({
            fill: new Fill({
              color: "black", // Any color will work here for masking
            }),
          })

          // Draw each feature as part of the clipping mask
          features.forEach((feature) => {
            vectorContext.drawFeature(feature, style)
          })

          // Restore the blending mode to the default
          ctx.globalCompositeOperation = "source-over"

          // Restore the original canvas state
          ctx.restore()
        })
    }

    const updateWMSLayers = (date) => {
        if (!map.value) {
            console.warn("Map is not ready yet.")
            return
        }

        if (!layerWMS.value || layerWMS.value.length === 0) {
            console.warn("No WMS layers available.")
            return
        }

        try {
            layerWMS.value.forEach(({ layer }) => {
                if (layer.getSource) {
                    const source = layer.getSource()
                    const params = source.getParams()

                    if (date) {
                        params.TIME = date
                    }

                    source.updateParams(params)
                    layer.changed()
                } else {
                    console.error("Layer does not have a source:", layer)
                }
            });
        } catch (error) {
            console.error("Failed to update WMS layer:", error)
        }
    }

    function showPopupAt(coord, message = '') {
        const popup = popupRef.value
        if (!popup || !map.value) return

        if (message) popup.textContent = message

        const pixel = map.value.getPixelFromCoordinate(coord)
        popup.style.left = `${pixel[0]}px`
        popup.style.top = `${pixel[1]}px`
        popup.style.opacity = 1

        // Hide after 2.5 seconds
        setTimeout(() => {
            if (popup) popup.style.opacity = 0
        }, 2500)
    }

    function placeMarkerAt(coord) {
        // Clear any existing marker
        markerSource.value.clear()

        // Add new marker
        const markerFeature = new Feature({
            geometry: new Point(coord)
        })

        markerSource.value.addFeature(markerFeature)
    }

    const enableWMSClickQuery = () => {
        map.value.on("singleclick", async (event) => {
            const clickCoord = event.coordinate

            // Check if click is inside the drawn polygon
            if (isCoordinateInsideGeoJson(clickCoord)) { 
                placeMarkerAt(clickCoord)
                handleWMSQueryAtCoordinate(clickCoord)
            } else {
                console.log("Click outside polygon — ignoring")
                showPopupAt(clickCoord, "Please click within your area of interest to get suitability data")
                // Optional: also clear marker if clicked outside
                markerSource.value.clear()
            }
        })
    }

    const isCoordinateInsideGeoJson = (coordinate) => {
        if (!props.geoJsonData) return false

        try {
            const features = new GeoJSON().readFeatures(props.geoJsonData, {
                featureProjection: "EPSG:3857"
            })

            for (const feature of features) {
                const geometry = feature.getGeometry()
                if (geometry && geometry.intersectsCoordinate(coordinate)) {
                    return true
                }
            }

            return false
        } catch (err) {
            console.error("Failed to parse GeoJSON for hit testing:", err)
            return false
        }
    }

    const handleWMSQueryAtCoordinate = async (coordinate) => {
        if (!coordinate) {
            console.warn("No coordinate provided to handleWMSQueryAtCoordinate")
            return
        }

        if (!layerWMS?.value || layerWMS.value.length === 0) {
            console.warn("No WMS layers available")
            return
        }

        // Transform to EPSG:4326 (lat/lon)
        const [lon, lat] = toLonLat(coordinate)
            
        if (xmlDoc.value == null) 
            await callGetCapabilities()

        if (xmlDoc.value) {
            for (const { layerName, layer } of layerWMS.value) {
                const source = layer.getSource() // Access the layer's source
                if (!source) {
                    console.warn(`Layer source is missing for ${layerName}`)
                    continue
                }

                try {
                    const timeSteps = fetchTimeSteps(layerName, xmlDoc.value)
                    const layerTitle = fetchLayerTitle(layerName, xmlDoc.value)
                    if (timeSteps.length > 0) {
                        // Convert timeSteps to Date objects, sort, and get start/end times
                        const sortedTimes = timeSteps.map((t) => new Date(t)).sort((a, b) => a - b)
                        const startTime = sortedTimes[0].toISOString() // Earliest time
                        const endTime = sortedTimes[sortedTimes.length - 1].toISOString() // Latest time

                        const timeSeries = await fetchTimeSeries(layerName, [lon, lat], startTime, endTime)
                        if (timeSeries.length > 0) {
                            const years = timeSeries.map((item) => new Date(item.time).getFullYear())
                            const scores = timeSeries.map((item) => item.value)
                            emit('update-graph', { years, scores, layerTitle })
                        } else {
                            console.warn(`No time series data for layer: ${layerName}`)
                        }           
                    } else {
                        console.warn(`No time steps available for layer: ${layerName}`)
                    }
                } catch (err) {
                    console.error(`Error processing layer ${layerName}:`, err)
                }
            }
        }
    }

    const callGetCapabilities = async () => {
        try {
            const response = await gs.get('', {
                params: {
                    SERVICE: "WMS",
                    VERSION: "1.3.0",
                    REQUEST: "GetCapabilities",
                },
            })

            const parser = new DOMParser()
            xmlDoc.value = parser.parseFromString(response.data, "text/xml")
        } catch (error) {
            console.error("Failed to get layer capabilities:", error)
        }
    }

    const fetchTimeSteps = (layerName, xmlDoc) => {
        try {
            // Find the specific layer in the GetCapabilities XML
            const layers = xmlDoc.getElementsByTagName("Layer")
            for (let i = 0; i < layers.length; i++) {
                const name = layers[i].getElementsByTagName("Name")[0]?.textContent
                if (name === layerName) {
                    const dimension = layers[i].getElementsByTagName("Dimension")[0]
                    if (dimension && dimension.textContent && dimension.getAttribute("name") === "time") {
                        return dimension.textContent.split(",") // Time steps as an array
                    }
                }
            }
        } catch (error) {
            console.error("Failed to fetch time steps:", error)
        }

        return []
    }

    // Helper function to fetch time series data
    const fetchTimeSeries = async (layerName, point, startTime, endTime) => {
        const [lon, lat] = point
        const width = 101
        const height = 101
        const bbox = `${lon},${lon},${lat},${lat}` // Example bounding box
        const wmsUrl = `${baseWmsUrl}?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetTimeSeries&FORMAT=image/jpeg&TIME=${startTime}/${endTime}&QUERY_LAYERS=${layerName}&STYLES&LAYERS=${layerName}&INFO_FORMAT=text/csv&FEATURE_COUNT=50&X=0&Y=0&SRS=EPSG:4326&WIDTH=${width}&HEIGHT=${height}&BBOX=${bbox}`;

        try {
            const response = await gs.get(wmsUrl)
            const csvData = response.data
            return parseCSV(csvData); // Parse CSV to usable format
        } catch (error) {
            console.error(`Failed to fetch time series for layer ${layerName}:`, error)
            return []
        }
    }

    const fetchLayerTitle = (layerName, xmlDoc) => {
        try {
            // Find the specific layer in the GetCapabilities XML
            const layers = xmlDoc.getElementsByTagName("Layer")
            for (let i = 0; i < layers.length; i++) {
                const name = layers[i].getElementsByTagName("Name")[0]?.textContent
                if (name === layerName) {
                    return layers[i].getElementsByTagName("Title")[0]?.textContent
                }
            }
        } catch (error) {
            console.error("Failed to fetch layer title:", error)
        }

        return []
    }

    function simulateClickFromGeoJson() {
        console.log("Triggering simulated WMS click from GeoJSON")

        const feature = props.geoJsonData?.features?.[0]
        const coords = feature?.geometry?.coordinates

        if (!coords || !Array.isArray(coords) || !coords.length || !Array.isArray(coords[0]) || !coords[0].length) {
            console.warn("Invalid or missing GeoJSON coordinates", coords)
            return
        }

        const point = fromLonLat(coords[0][0])

        handleWMSQueryAtCoordinate(point)
    }

    // Parse CSV response
    const parseCSV = (data) => {
        const lines = data.split("\n")
        const result = []
        for (let i = 3; i < lines.length; i++) {
            const line = lines[i].trim()
            if (line) {
                const [time, value] = line.split(",")
                result.push({ time, value: parseFloat(value) })
            }
        }
        return result
    }

    const loadGeoJsonData = (data) => {
        const features = new GeoJSON().readFeatures(data, {
            featureProjection: "EPSG:3857", // Projection for OpenLayers
        })

        // Clear the existing vector source
        vectorSource.value.clear()

        // Add the new features to the vector source
        vectorSource.value.addFeatures(features)

        // Fit the map view to the extent of the new features
        if (features.length > 0) {
            map.value.getView().fit(vectorSource.value.getExtent(), { padding: [50, 50, 50, 50] })
        }
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
        hasPolygons.value = vectorSource.value.getFeatures().length > 0
    }

    function sliderStyle(i, opacity) {
        const color = palette[i % palette.length];
        const pct = Math.max(0, Math.min(1, Number(opacity || 0))) * 100;
        return {
            accentColor: color,              // modern browsers color the thumb
            '--slider-color': color,         // used by CSS below
            '--slider-percent': `${pct}%`,   // used by CSS gradient fill
        };
    }
</script>
  
  <style scoped>
    .map-wrapper {
        position: relative;
        width: 100%;
        height: auto;
        margin-top: 10px;
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
  
    .legend-container {
      position: absolute;
      top: 12px;
      right: 12px;
      z-index: 1000; /* Ensure it appears above the map */
      background-color: rgba(255, 255, 255, 0.8); /* Semi-transparent background */
      padding: 10px;
      border-radius: 8px;
      box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
      max-width: 195px;
      height: 400px;
      display: flex;
      flex-direction: row;
      justify-content: space-evenly;
      gap: 12px;
    }
    .legend-item {
      display: flex;
      flex-direction: row;
      align-items: center;
      gap: 5px;
    }
    .legend-image {
      display: block;
      width: 55px; /* Adjust width */
      height: 255px;  /* 215px */ /* Maintain aspect ratio */
      margin: auto;
      border: 1px solid #ccc;
      border-radius: 5px;
    }
    .legend-label {
      writing-mode: vertical-rl; /* Vertical text */
      transform: rotate(180deg); /* Flip to correct orientation 180 */
      text-align: center;
      font-size: 11.5px;
      font-weight: bold;
      color: #333;
      white-space: nowrap;
    }

    .opacity-controls {
        margin-top: 10px;
        margin-bottom: 25px;
        padding-top: 5px;
        padding-bottom: 5px;

        display: flex;
        flex-direction: row;
        flex-wrap: wrap;
        align-content: center;
        justify-content: space-evenly;
        align-items: center;
        row-gap: 5px;

        font-size: 12px;
        border: 1px solid #ccc;
        border-radius: 5px;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
    }

    .inner-controls {
        display: flex;
        flex-direction: row;
        flex-wrap: wrap;
        align-content: center;
        justify-content: space-evenly;
        align-items: center;        
    }

        /* ------- Slider coloring ------- */
    .opacity-controls input[type="range"] {
        appearance: none;
        width: 160px;
        height: 6px;
        border-radius: 9999px;
        background: linear-gradient(
            to right,
            var(--slider-color) 0 var(--slider-percent),
            #e5e7eb var(--slider-percent) 100%
        );
        outline: none;
    }

    /* WebKit thumb (Chrome, Edge, Safari) */
    .opacity-controls input[type="range"]::-webkit-slider-thumb{
        appearance: none;
        width: 14px;
        height: 14px;
        border-radius: 50%;
        background: var(--slider-color);
        border: 0;
        margin-top: -4px; /* center on 6px track */
        cursor: pointer;
    }
    /* WebKit track */
    .opacity-controls input[type="range"]::-webkit-slider-runnable-track{
        height: 6px;
        border-radius: 9999px;
        background: transparent;
    }

    /* Firefox */
    .opacity-controls input[type="range"]::-moz-range-track{
        height: 6px;
        border-radius: 9999px;
        background: #e5e7eb;
    }
    .opacity-controls input[type="range"]::-moz-range-progress{
        height: 6px;
        border-radius: 9999px;
        background: var(--slider-color);
    }

    /* Optional focus ring */
    .opacity-controls input[type="range"]:focus{
        box-shadow: 0 0 0 3px color-mix(in oklab, var(--slider-color) 30%, white);
    }
    /* ------- Slider coloring ------- */

  
    .controls {
      display: flex;
      gap: 10px;
      margin-top: 10px;
    }
    button {
      padding: 5px 10px;
      background-color: #4caf50;
      color: white;
      border: none;
      cursor: pointer;
      border-radius: 4px;
      font-size: 14px;
    }
    button:hover {
      background-color: #45a049;
    }
    .map-popup {
        position: absolute;
        background-color: rgba(0, 0, 0, 0.85);
        color: #fff;
        padding: 6px 10px;
        border-radius: 4px;
        font-size: 13px;
        white-space: nowrap;
        transform: translate(-50%, -100%);
        pointer-events: none;
        transition: opacity 0.3s ease;
        opacity: 0;
        z-index: 1100;
    }

    .top-explanation {
        margin-bottom: 10px;
    }

    .bottom-explanation {
        /* margin-top: 10px; */
        margin-bottom: 30px;
    }
  </style>
    