import axios from 'axios'

// Route GeoServer through nginx so it's same-origin and no CORS needed.
// In .env:  VITE_GS_BASE=/geoserver
const gs = axios.create({
  baseURL: import.meta.env.VITE_WMS_BASE_URL
})

// IMPORTANT: never add Authorization here
export default gs
