export function isGeoJSON(obj) {
  if (!obj || typeof obj !== 'object') return false
  const t = obj.type
  if (t === 'FeatureCollection') return Array.isArray(obj.features)
  if (t === 'Feature') return !!obj.geometry
  if (t === 'GeometryCollection') return Array.isArray(obj.geometries)
  const geom = ['Point','MultiPoint','LineString','MultiLineString','Polygon','MultiPolygon']
  return geom.includes(t) && Array.isArray(obj.coordinates)
}

export function summarizeGeoJSON(obj) {
  if (!obj) return ''
  if (obj.type === 'FeatureCollection') {
    const n = Array.isArray(obj.features) ? obj.features.length : 0
    const types = (obj.features || []).map(f => f?.geometry?.type).filter(Boolean)
    const uniq = [...new Set(types)]
    return `📍 GeoJSON sent (${n} feature${n === 1 ? '' : 's'}${uniq.length ? `: ${uniq.join(', ')}` : ''})`
  }
  if (obj.type === 'Feature') return `📍 GeoJSON Feature sent (${obj.geometry?.type || 'Unknown'})`
  return `📍 GeoJSON ${obj.type} sent`
}

export function tryParseGeoJSON(raw) {
  if (typeof raw !== 'string') return null
  try {
    const parsed = JSON.parse(raw)
    return isGeoJSON(parsed) ? parsed : null
  } catch {
    return null
  }
}
