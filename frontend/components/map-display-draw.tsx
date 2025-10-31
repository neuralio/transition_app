'use client'

/**
 * MapDisplayDraw Component
 *
 * Interactive map component with polygon drawing capabilities.
 * - Uses OpenLayers for map rendering
 * - ArcGIS World Imagery satellite basemap
 * - Allows drawing, modifying, and deleting polygons (supports multiple)
 * - Exports GeoJSON of drawn polygons
 * - Designed for spatial filtering in ML-ABM simulations
 */

import React, { useEffect, useRef, useState } from 'react'
import { useTheme } from 'next-themes'

import {
  Map,
  View,
  TileLayer,
  VectorLayer,
  VectorSource,
  XYZ,
  GeoJSON,
  Draw,
  Modify,
  Feature,
  Polygon,
  fromLonLat
} from '@/lib/map/mapUtils'

import { Style, Stroke, Fill } from 'ol/style'

import { areaConfigs, PILOT_THESSALONIKI } from '@/lib/map/areaConfigs'

// MODULE-LEVEL SINGLETON: VectorSource persists across component remounts
// This is the KEY to maintaining drawn polygons when hiding/showing the map
let globalVectorSource: VectorSource | null = null

function getGlobalVectorSource(): VectorSource {
  if (!globalVectorSource) {
    console.log('🆕 Creating NEW global VectorSource singleton')
    globalVectorSource = new VectorSource()
  } else {
    console.log('♻️ Reusing existing global VectorSource singleton')
  }
  return globalVectorSource
}
import { Button } from '@/components/ui/button'
import { DateRangePicker } from '@/components/ui/date-range-picker'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Loader2, CheckCircle2, AlertCircle, Terminal } from 'lucide-react'

interface MapDisplayDrawProps {
  pilotArea?: string
  onGeojsonChange?: (geojson: string) => void
  onNdviRequest?: (geojson: string, startDate: string, endDate: string) => Promise<void>
  ndviAlert?: {
    type: 'success' | 'warning' | 'error'
    title: string
    message: string
  } | null
  onDismissAlert?: () => void
  className?: string
  compact?: boolean
  isVisible?: boolean  // Track parent visibility to refresh map size
}

export function MapDisplayDraw({
  pilotArea = 'thessaloniki',
  onGeojsonChange,
  onNdviRequest,
  ndviAlert,
  onDismissAlert,
  className = '',
  compact = false,
  isVisible = true  // Default to visible
}: MapDisplayDrawProps) {
  const { resolvedTheme } = useTheme()
  const mapRef = useRef<HTMLDivElement>(null)
  const mapInstanceRef = useRef<Map | null>(null)
  // Use singleton VectorSource instead of creating new one per component instance
  const vectorSourceRef = useRef<VectorSource>(getGlobalVectorSource())
  const [hasPolygons, setHasPolygons] = useState(false)
  const [polygonCount, setPolygonCount] = useState(0)
  const [primaryColor, setPrimaryColor] = useState<string>('#8b5cf6')

  // Track if map has been initialized to prevent duplicate initialization
  const isMapInitializedRef = useRef(false)

  // NDVI processing state
  const [isProcessingNDVI, setIsProcessingNDVI] = useState(false)
  // User MUST select dates - no defaults
  const [dateRange, setDateRange] = useState({ from: '', to: '' })

  // Get the actual primary color from CSS variables
  useEffect(() => {
    const root = document.documentElement
    const computedStyle = getComputedStyle(root)
    const primary = computedStyle.getPropertyValue('--primary').trim()

    // The actual primary color from the screenshot is #2563eb (blue-600)
    setPrimaryColor('#2563eb')
  }, [])

  useEffect(() => {
    console.log('🗺️ MapDisplayDraw: Map initialization useEffect triggered')
    console.log('   pilotArea:', pilotArea)
    console.log('   isMapInitializedRef.current:', isMapInitializedRef.current)

    if (!mapRef.current) return

    // PREVENT RE-INITIALIZATION - Only initialize once!
    if (isMapInitializedRef.current) {
      console.log('⚠️ Map already initialized - skipping re-initialization')

      // BUT: Check if singleton VectorSource has features and emit them to parent
      const existingFeatures = vectorSourceRef.current.getFeatures()
      if (existingFeatures.length > 0 && onGeojsonChange) {
        console.log(`📤 Found ${existingFeatures.length} existing features in singleton - emitting to parent`)

        // Export existing features as GeoJSON
        const geojsonFormat = new GeoJSON()
        const geojsonStr = geojsonFormat.writeFeatures(existingFeatures, {
          featureProjection: 'EPSG:3857',
          dataProjection: 'EPSG:4326'
        })
        const geojson = JSON.parse(geojsonStr)
        const geojsonString = JSON.stringify(geojson, null, 2)

        console.log('📤 Emitting existing GeoJSON to parent, length:', geojsonString.length)
        onGeojsonChange(geojsonString)

        // Update UI state
        setHasPolygons(true)
        setPolygonCount(existingFeatures.length)
      }

      return
    }

    console.log('✅ Proceeding with map initialization...')
    isMapInitializedRef.current = true

    // Initialize map
    const areaConfig = areaConfigs[pilotArea] || PILOT_THESSALONIKI

    // Base layer - ArcGIS Satellite Imagery
    const satelliteLayer = new TileLayer({
      source: new XYZ({
        url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attributions: '&copy; <a href="https://www.esri.com/">Esri</a> contributors'
      })
    })

    // Data bounds rectangle layer (highlight available data area)
    const boundsSource = new VectorSource()
    const { bounds } = areaConfig

    // Create rectangle feature from data bounds
    const boundsPolygon = new Polygon([[
      fromLonLat([bounds.minLon, bounds.minLat]),
      fromLonLat([bounds.maxLon, bounds.minLat]),
      fromLonLat([bounds.maxLon, bounds.maxLat]),
      fromLonLat([bounds.minLon, bounds.maxLat]),
      fromLonLat([bounds.minLon, bounds.minLat])
    ]])

    const boundsFeature = new Feature({
      geometry: boundsPolygon
    })

    // Style: Use primary theme color #2563eb (blue-600 from globals.css)
    const themeBlue = '#2563eb'
    boundsFeature.setStyle(new Style({
      stroke: new Stroke({
        color: themeBlue,
        width: 3
      }),
      fill: new Fill({
        color: 'rgba(37, 99, 235, 0.15)' // blue-600 with 15% opacity
      })
    }))

    boundsSource.addFeature(boundsFeature)

    const boundsLayer = new VectorLayer({
      source: boundsSource,
      style: new Style({
        stroke: new Stroke({
          color: themeBlue,
          width: 3
        }),
        fill: new Fill({
          color: 'rgba(37, 99, 235, 0.15)'
        })
      })
    })

    // Vector layer for drawing polygons
    const vectorLayer = new VectorLayer({
      source: vectorSourceRef.current
    })

    // Create map instance (bounds layer first, then user drawings on top)
    const map = new Map({
      target: mapRef.current,
      layers: [satelliteLayer, boundsLayer, vectorLayer],
      view: new View({
        center: fromLonLat(areaConfig.center), // Transform [lon, lat] to EPSG:3857
        zoom: areaConfig.zoom
      })
    })

    mapInstanceRef.current = map

    // Add draw interaction (Polygon)
    const drawInteraction = new Draw({
      source: vectorSourceRef.current,
      type: 'Polygon'
    })
    map.addInteraction(drawInteraction)

    // Add modify interaction (edit existing polygons)
    const modifyInteraction = new Modify({
      source: vectorSourceRef.current
    })
    map.addInteraction(modifyInteraction)

    // Update polygon state and emit GeoJSON when drawing completes
    drawInteraction.on('drawend', () => {
      setTimeout(() => {
        updatePolygonState()
        emitGeoJSON()
      }, 0)
    })

    // Update polygon state and emit GeoJSON when modifying completes
    modifyInteraction.on('modifyend', () => {
      updatePolygonState()
      emitGeoJSON()
    })

    // Listen to vector source changes
    vectorSourceRef.current.on('addfeature', updatePolygonState)
    vectorSourceRef.current.on('removefeature', updatePolygonState)
    vectorSourceRef.current.on('clear', updatePolygonState)

    // Cleanup: DON'T destroy map/source, just detach from DOM
    // The singleton VectorSource persists, keeping all drawn polygons
    return () => {
      console.log('🧹 MapDisplayDraw: Cleanup (component unmounting)')
      console.log('   NOT destroying map - just detaching from DOM')
      console.log('   VectorSource features will persist:', vectorSourceRef.current.getFeatures().length)
      // DON'T call map.setTarget(undefined) - it breaks the map
      // DON'T reset isMapInitializedRef - we want to skip re-init on remount
      // The map and VectorSource persist in memory
    }
  }, [pilotArea]) // Only re-initialize if pilot area changes

  // Watch for isVisible prop changes and refresh map
  // This is the PROPER OpenLayers way to handle show/hide
  useEffect(() => {
    console.log('🔍 VISIBILITY EFFECT: isVisible =', isVisible, ', mapInstance exists =', !!mapInstanceRef.current)

    if (!mapInstanceRef.current) {
      console.log('⚠️ Map not initialized yet, skipping')
      return
    }

    // Check current features BEFORE any update
    const featuresBefore = vectorSourceRef.current?.getFeatures() || []
    console.log(`📊 BEFORE update: ${featuresBefore.length} features in VectorSource`)

    if (isVisible) {
      console.log('👁️ Map becoming VISIBLE - refreshing...')

      // Update map size (CRITICAL for OpenLayers after CSS hide/show)
      setTimeout(() => {
        console.log('🔄 Executing refresh logic...')
        console.log('  Step 1: Calling map.updateSize()')
        mapInstanceRef.current?.updateSize()

        // Features are ALREADY in VectorSource - just verify
        const features = vectorSourceRef.current?.getFeatures() || []
        console.log(`  Step 2: VectorSource now has ${features.length} features`)

        // Debug each feature
        features.forEach((feature, idx) => {
          const geom = feature.getGeometry()
          console.log(`    Feature ${idx}: type=${geom?.getType()}`)
        })

        setHasPolygons(features.length > 0)
        setPolygonCount(features.length)

        // Force re-render of vector layer
        const layers = mapInstanceRef.current?.getLayers().getArray()
        console.log(`  Step 3: Checking ${layers?.length} map layers`)
        layers?.forEach((layer, idx) => {
          console.log(`    Layer ${idx}: ${layer.constructor.name}`)
          if (layer instanceof VectorLayer) {
            const source = layer.getSource()
            const layerFeatures = source?.getFeatures() || []
            console.log(`      → VectorLayer source has ${layerFeatures.length} features`)
            console.log(`      → Calling layer.changed() to force re-render`)
            layer.changed()
          }
        })

        console.log('✅ Refresh complete')
      }, 100)
    } else {
      console.log('👁️ Map becoming HIDDEN')
    }
  }, [isVisible])

  const updatePolygonState = () => {
    const features = vectorSourceRef.current.getFeatures()
    const count = features.length
    console.log(`📊 Polygon state updated: ${count} features in VectorSource`)
    setHasPolygons(count > 0)
    setPolygonCount(count)
  }

  const exportGeoJSON = (): object | null => {
    const features = vectorSourceRef.current.getFeatures()
    if (features.length === 0) return null

    console.log(`📊 Exporting ${features.length} features from vector source`)

    const geojsonFormat = new GeoJSON()
    const geojsonStr = geojsonFormat.writeFeatures(features, {
      featureProjection: 'EPSG:3857', // OpenLayers projection
      dataProjection: 'EPSG:4326' // WGS84 (standard lat/lon)
    })

    const geojson = JSON.parse(geojsonStr)

    // Debug: Log first coordinate of each polygon
    if (geojson.features && geojson.features.length > 0) {
      geojson.features.forEach((feature: any, idx: number) => {
        if (feature.geometry && feature.geometry.coordinates && feature.geometry.coordinates[0]) {
          const firstCoord = feature.geometry.coordinates[0][0]
          console.log(`  Feature ${idx + 1} first coord:`, firstCoord)
        }
      })
    }

    return geojson
  }

  const emitGeoJSON = () => {
    const geojson = exportGeoJSON()
    console.log('🗺️ MapDisplayDraw: emitGeoJSON called')
    console.log('🗺️ MapDisplayDraw: geojson exists?', !!geojson)
    console.log('🗺️ MapDisplayDraw: geojson:', geojson ? JSON.stringify(geojson).substring(0, 200) : 'null')
    if (onGeojsonChange) {
      const geojsonStr = geojson ? JSON.stringify(geojson, null, 2) : ''
      console.log('🗺️ MapDisplayDraw: Calling onGeojsonChange with string length:', geojsonStr.length)
      onGeojsonChange(geojsonStr)
    } else {
      console.log('⚠️ MapDisplayDraw: onGeojsonChange callback NOT provided!')
    }
  }

  const handleClearLast = () => {
    const features = vectorSourceRef.current.getFeatures()
    if (features.length > 0) {
      vectorSourceRef.current.removeFeature(features[features.length - 1])
      emitGeoJSON()
    }
  }

  const handleClearAll = () => {
    vectorSourceRef.current.clear()
    if (onGeojsonChange) {
      onGeojsonChange('')
    }
  }

  const handleCopyGeoJSON = async () => {
    const geojson = exportGeoJSON()
    if (geojson) {
      const jsonStr = JSON.stringify(geojson, null, 2)

      // Log to console (silent)
      console.log('📊 GeoJSON copied for ' + polygonCount + ' polygon(s)')

      // Copy to clipboard silently
      try {
        await navigator.clipboard.writeText(jsonStr)
        console.log('✅ Copied to clipboard successfully')
      } catch (err) {
        console.error('❌ Failed to copy to clipboard:', err)
      }
    }
  }

  const handleGetNDVI = async () => {
    const geojson = exportGeoJSON()
    if (!geojson || !dateRange.from || !dateRange.to) {
      alert('Please draw at least one polygon and select a date range')
      return
    }

    setIsProcessingNDVI(true)

    try {
      if (onNdviRequest) {
        await onNdviRequest(JSON.stringify(geojson), dateRange.from, dateRange.to)
        console.log('✅ NDVI processing completed')
      } else {
        console.warn('⚠️ onNdviRequest callback not provided')
      }
    } catch (error) {
      console.error('❌ NDVI processing failed:', error)
      alert(`NDVI processing failed: ${error}`)
    } finally {
      setIsProcessingNDVI(false)
    }
  }

  const handleDateChange = (newDateRange: { from: string; to: string }) => {
    setDateRange(newDateRange)
    console.log('📅 Date range updated:', newDateRange)
  }

  return (
    <div className={`flex flex-col w-full ${className}`}>
      {/* Data Bounds Info */}
      {!compact && (
        <div className="mb-2 p-3 rounded-lg bg-primary">
          <p className="text-sm text-primary-foreground font-medium">
            ⚠️ Data Availability: Blue rectangle shows Thessaloniki area with available data. Please draw polygon{polygonCount > 1 ? 's' : ''} inside this area.
            {hasPolygons && (
              <span className="ml-2 font-bold">
                {polygonCount} polygon{polygonCount !== 1 ? 's' : ''} will be applied to queries.
              </span>
            )}
          </p>
        </div>
      )}

      {/* Compact Info for Sidebar */}
      {compact && (
        <div className="mb-2 p-3 rounded-lg bg-primary">
          <p className="text-sm text-primary-foreground font-medium">
            ⚠️ Draw inside blue area
            {hasPolygons && <span className="ml-2">({polygonCount} selected)</span>}
          </p>
        </div>
      )}

      {/* Map Container */}
      <div
        ref={mapRef}
        className={`w-full border border-gray-300 dark:border-gray-700 rounded-md shadow-md bg-gray-100 dark:bg-gray-900 ${
          compact ? 'h-[400px]' : 'h-[450px]'
        }`}
      />

      {/* NDVI Processing Alert - Shows right after map */}
      {ndviAlert && (
        <div className="mt-3">
          <Alert
            variant={ndviAlert.type === 'error' ? 'destructive' : 'default'}
            className="relative"
          >
            {ndviAlert.type === 'success' && <CheckCircle2 className="h-4 w-4" />}
            {ndviAlert.type === 'warning' && <AlertCircle className="h-4 w-4" />}
            {ndviAlert.type === 'error' && <Terminal className="h-4 w-4" />}
            <AlertTitle>{ndviAlert.title}</AlertTitle>
            <AlertDescription className="text-sm">
              {ndviAlert.message}
            </AlertDescription>
            {onDismissAlert && (
              <button
                onClick={onDismissAlert}
                className="absolute top-2 right-2 text-muted-foreground hover:text-foreground"
              >
                ✕
              </button>
            )}
          </Alert>
        </div>
      )}

      {/* Controls */}
      <div className={`flex gap-2 mt-3 ${compact ? 'flex-col' : ''}`}>
        <Button
          onClick={handleClearLast}
          disabled={!hasPolygons}
          variant="default"
          size="sm"
        >
          Clear Last
        </Button>
        <Button
          onClick={handleClearAll}
          disabled={!hasPolygons}
          variant="default"
          size="sm"
        >
          Clear All
        </Button>
        <Button
          onClick={handleCopyGeoJSON}
          disabled={!hasPolygons}
          variant="outline"
          size="sm"
        >
          Copy GeoJSON
        </Button>
      </div>
    </div>
  )
}
