// Area configurations for different pilot regions
// Currently supports Thessaloniki pilot area

export interface AreaConfig {
  name: string
  center: [number, number] // [longitude, latitude]
  zoom: number
  bounds: {
    minLat: number
    maxLat: number
    minLon: number
    maxLon: number
  }
}

// Thessaloniki Pilot Area Configuration
export const PILOT_THESSALONIKI: AreaConfig = {
  name: 'Thessaloniki',
  center: [22.9, 40.6], // Longitude, Latitude
  zoom: 9,
  bounds: {
    minLat: 40.4,
    maxLat: 40.9,
    minLon: 22.5,
    maxLon: 22.9,
  },
}

// Collection of all available area configurations
export const areaConfigs: Record<string, AreaConfig> = {
  thessaloniki: PILOT_THESSALONIKI,
  // Future pilot areas can be added here
  // Example:
  // paris: PILOT_PARIS,
  // berlin: PILOT_BERLIN,
}

// Helper function to validate coordinates against area bounds
export function isWithinBounds(
  lat: number,
  lon: number,
  area: AreaConfig
): boolean {
  return (
    lat >= area.bounds.minLat &&
    lat <= area.bounds.maxLat &&
    lon >= area.bounds.minLon &&
    lon <= area.bounds.maxLon
  )
}

// Helper function to get area config by name
export function getAreaConfig(name: string): AreaConfig | undefined {
  return areaConfigs[name.toLowerCase()]
}
