// OpenLayers exports for map functionality
// This file provides centralized exports for all OpenLayers components

import OLMap from 'ol/Map'
import OLView from 'ol/View'
import OLTileLayer from 'ol/layer/Tile'
import OLVectorLayer from 'ol/layer/Vector'
import OLVectorSource from 'ol/source/Vector'
import OLXYZ from 'ol/source/XYZ'
import OLGeoJSON from 'ol/format/GeoJSON'
import OLDraw from 'ol/interaction/Draw'
import OLModify from 'ol/interaction/Modify'
import OLFeature from 'ol/Feature'
import OLPolygon from 'ol/geom/Polygon'
import { fromLonLat as olFromLonLat, toLonLat as olToLonLat } from 'ol/proj'

// Re-export with simpler names
export const Map = OLMap
export const View = OLView
export const TileLayer = OLTileLayer
export const VectorLayer = OLVectorLayer
export const VectorSource = OLVectorSource
export const XYZ = OLXYZ
export const GeoJSON = OLGeoJSON
export const Draw = OLDraw
export const Modify = OLModify
export const Feature = OLFeature
export const Polygon = OLPolygon
export const fromLonLat = olFromLonLat
export const toLonLat = olToLonLat

// Type exports
export type { Map as MapType } from 'ol'
export type { Feature as FeatureType } from 'ol'
