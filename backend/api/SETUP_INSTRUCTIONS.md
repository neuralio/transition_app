# Backend API Setup Instructions

## ✅ What's Been Created

The Sentinel-2 NDVI processing API endpoint has been created at:
- `backend/api/routes/sentinel.py` - FastAPI router with `/api/sentinel/compute-indices` endpoint

## 🔧 How to Register the API in Your FastAPI App

### Step 1: Find Your Main FastAPI Application

Look for your main FastAPI app file. It's typically named one of:
- `backend/api/main.py`
- `backend/api/app.py`
- `backend/main.py`
- `app.py`

### Step 2: Add the Import

At the top of your main FastAPI file, add:

```python
from backend.api.routes.sentinel import router as sentinel_router
```

### Step 3: Register the Router

After creating your FastAPI app instance, register the router:

```python
from fastapi import FastAPI
from backend.api.routes.sentinel import router as sentinel_router

app = FastAPI()

# Register Sentinel-2 NDVI processing router
app.include_router(sentinel_router)

# ... rest of your app code
```

### Step 4: Test the Endpoint

Start your FastAPI server and test:

```bash
# Example curl request
curl -X POST "http://localhost:8000/api/sentinel/compute-indices" \\
  -H "Content-Type: application/json" \\
  -d '{
    "geojson": {
      "type": "FeatureCollection",
      "features": [{
        "type": "Feature",
        "geometry": {
          "type": "Polygon",
          "coordinates": [[[22.5, 40.5], [22.6, 40.5], [22.6, 40.6], [22.5, 40.6], [22.5, 40.5]]]
        }
      }]
    },
    "start_date": "2024-01-01",
    "end_date": "2024-01-15",
    "indices": ["NDVI", "NDWI"]
  }'
```

## 🎨 Frontend Integration

### In Your React Component

Update your map component to call the backend API:

```typescript
// In your page or parent component
import { MapDisplayDraw } from '@/components/map-display-draw'

function YourPage() {
  const handleNdviRequest = async (geojson: string, startDate: string, endDate: string) => {
    try {
      const response = await fetch('/api/sentinel/compute-indices', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          geojson: JSON.parse(geojson),
          start_date: startDate,
          end_date: endDate,
          indices: ['NDVI', 'NDWI']
        })
      })

      if (!response.ok) {
        throw new Error(`API error: ${response.statusText}`)
      }

      const result = await response.json()
      console.log('✅ NDVI results:', result)

      // Display results (e.g., update map with enriched GeoJSON)
      displayNdviResults(result.geojson)

    } catch (error) {
      console.error('❌ NDVI processing failed:', error)
      alert(`Failed to process NDVI: ${error}`)
    }
  }

  return (
    <MapDisplayDraw
      onNdviRequest={handleNdviRequest}
    />
  )
}
```

## 📝 Example Full FastAPI App

Here's a complete example:

```python
# backend/api/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api.routes.sentinel import router as sentinel_router

app = FastAPI(
    title="TRANSITION API",
    description="EO-Informed Agent-Based Models API",
    version="1.0.0"
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js default port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(sentinel_router)

@app.get("/")
def read_root():
    return {"message": "TRANSITION API - EO-Informed Irrigation"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

## 🧪 Testing the Full Workflow

1. **Start Backend**:
   ```bash
   cd /home/ggous/Models/Transition
   python backend/api/main.py
   ```

2. **Start Frontend**:
   ```bash
   cd frontend
   npm run dev
   ```

3. **Test in Browser**:
   - Open http://localhost:3000
   - Draw a polygon on the map
   - The date range should already be set (last 30 days)
   - Click "📊 Get NDVI" button
   - Wait 2-5 minutes for processing
   - Results will appear in console (check browser DevTools)

## 🔍 Debugging

If the button is not clickable:

1. **Check polygon is drawn**: Open browser DevTools → Console → should see "📊 GeoJSON exported"
2. **Check date range**: Should show dates like "2024-10-24 → 2024-11-23"
3. **Check button state**: Button should be green with "📊 Get NDVI" text

If processing fails:

1. **Check backend logs**: Look for errors in FastAPI console
2. **Check script path**: Verify `/home/ggous/Models/Transition/use_cases/irrigation/Sentinel/dowmload_process_sentinel2_data.py` exists
3. **Check dependencies**: Make sure `rasterio`, `shapely`, `pystac-client` are installed

## 📦 Required Dependencies

Make sure these are installed in your Python environment:

```bash
pip install fastapi uvicorn pyyaml rasterio shapely pystac-client
```

## ✅ Summary

- ✅ Backend API endpoint created: `POST /api/sentinel/compute-indices`
- ✅ Frontend button fixed: Dates now default to last 30 days
- ✅ Script execution: Uses `python3 dowmload_process_sentinel2_data.py --config temp.yaml`
- ✅ Results: Returns enriched GeoJSON with NDVI statistics per polygon

**Next**: Register the router in your FastAPI main app and test!
