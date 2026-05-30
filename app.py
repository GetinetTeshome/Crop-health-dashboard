import streamlit as st
import ee
import geemap.foliumap as geemap
import datetime

# 1. Initialize Google Earth Engine
# Note: In production, you will use a Service Account key for seamless user access.
try:
    ee.Initialize()
except Exception as e:
    st.error("EE Authentication required. Please run 'earthengine authenticate' in your terminal.")
    st.stop()

# Set up Streamlit Web Interface
st.set_page_config(layout="wide")
st.title("🇪🇹 Automated NDVI Crop-Health Dashboard")
st.write("Lightweight satellite monitoring for Ethiopian Smallholder Cooperatives.")

# 2. Sidebar Controls for the User
st.sidebar.header("Select Region & Date")
region_select = st.sidebar.selectbox(
    "Target Area",
    ["Oromia (Bale Zone Wheat)", "Amhara (Teff Region)", "Sidama (Coffee Zones)"]
)

# Set coordinates based on selection
regions = {
    "Oromia (Bale Zone Wheat)": [39.90, 7.10],
    "Amhara (Teff Region)": [37.70, 11.60],
    "Sidama (Coffee Zones)": [38.50, 6.70]
}
coords = regions[region_select]

# Date selection (Sentinel-2 data available from 2015-present)
start_date = st.sidebar.date_input("Start Date", datetime.date(2026, 1, 1))
end_date = st.sidebar.date_input("End Date", datetime.date(2026, 5, 30))

# 3. Cloud-Based Satellite Processing Function
def get_ndvi_map(lon, lat, start, end):
    # Create a point geometry and buffer it to simulate a cooperative boundary
    point = ee.Geometry.Point([lon, lat])
    aoi = point.buffer(5000) # 5km radius area of interest
    
    # Pull Sentinel-2 Level-2A (Bottom-of-Atmosphere corrected) imagery
    s2 = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
        .filterBounds(aoi) \
        .filterDate(start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d')) \
        .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20)) \
        .median() # Take the median to remove fleeting clouds
        
    # Calculate NDVI: (NIR - Red) / (NIR + Red)
    # Sentinel-2: Band 8 is NIR, Band 4 is Red
    ndvi = s2.normalizedDifference(['B8', 'B4']).rename('NDVI')
    
    return ndvi, aoi

# 4. Process and Render Map
if st.button("Generate Crop Health Analysis"):
    with st.spinner("Fetching Sentinel-2 cloud data..."):
        try:
            ndvi_image, aoi_geom = get_ndvi_map(coords[0], coords[1], start_date, end_date)
            
            # Create interactive Leaflet map centered at our region
            Map = geemap.Map(center=[coords[1], coords[0]], zoom=12)
            
            # Define simple visual parameters (Red = Bare soil/Dead, Yellow = Stressed, Green = Healthy)
            ndvi_vis = {
                'min': 0.0,
                'max': 0.8,
                'palette': ['#d73027', '#f46d43', '#fdae61', '#fee08b', '#d9ef8b', '#a6d96a', '#66bd63', '#1a9850']
            }
            
            # Add layers to the map data structure
            Map.addLayer(ndvi_image.clip(aoi_geom), ndvi_vis, 'Crop Health (NDVI)')
            
            # Render map on the Streamlit web front-end
            st.success(f"Showing health metrics for {region_select}")
            Map.to_streamlit(height=600)
            
            # Helpful context for Extension Agents
            st.info("💡 **How to interpret:** Deep Green zones indicate dense, healthy vegetative growth. Yellow-to-Red patches indicate moisture stress, pest damage, or clear soil.")
            
        except Exception as e:
            st.error(f"No clear imagery found for this date range. Try broadening your dates. Error: {e}")