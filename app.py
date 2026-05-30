import streamlit as st
import ee
import folium
from streamlit_folium import folium_static
import datetime
import json

# 1. Initialize Google Earth Engine using Streamlit Secrets
try:
    # Pull the credentials seamlessly from your Secrets panel
    secret_creds = st.secrets["gcp_service_account"]
    
    # Parse into the format Google Earth Engine expects
    creds_dict = json.loads(json.dumps(secret_creds))
    ee_creds = ee.ServiceAccountCredentials(creds_dict['client_email'], key_data=creds_dict['private_key'])
    
    ee.Initialize(ee_creds)
except Exception as e:
    st.error(f"Failed to authenticate with Google Earth Engine: {e}")
    st.info("Please verify your 'gcp_service_account' secrets are properly filled out in the Streamlit Dashboard.")
    st.stop()

# Set up Streamlit Web Interface Layout
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

start_date = st.sidebar.date_input("Start Date", datetime.date(2025, 9, 1))
end_date = st.sidebar.date_input("End Date", datetime.date(2026, 5, 30))

# 3. Cloud-Based Satellite Processing Function
def get_ndvi_url(lon, lat, start, end):
    point = ee.Geometry.Point([lon, lat])
    aoi = point.buffer(5000) # 5km radius area of interest
    
    # Pull Sentinel-2 Level-2A imagery over the boundary
    s2 = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
        .filterBounds(aoi) \
        .filterDate(start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d')) \
        .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20)) \
        .median()
        
    # Calculate NDVI: (NIR - Red) / (NIR + Red)
    ndvi = s2.normalizedDifference(['B8', 'B4']).rename('NDVI')
    
    # Define simple color parameters (Red = Stressed/Soil, Green = Highly Healthy)
    ndvi_vis = {
        'min': 0.0,
        'max': 0.8,
        'palette': ['#d73027', '#f46d43', '#fdae61', '#fee08b', '#d9ef8b', '#a6d96a', '#66bd63', '#1a9850']
    }
    
    # Generate a lightweight map tile URL directly from Google's servers
    map_id_dict = ee.Image(ndvi.clip(aoi)).getMapId(ndvi_vis)
    return map_id_dict['tile_fetcher'].url_format, aoi.getInfo()['coordinates']

# 4. Process and Render Map via Pure Folium
if st.button("Generate Crop Health Analysis"):
    with st.spinner("Fetching Sentinel-2 cloud data..."):
        try:
            tile_url, aoi_coords = get_ndvi_url(coords[0], coords[1], start_date, end_date)
            
            # Initialize a standard Leaflet map centered on our targets
            m = folium.Map(location=[coords[1], coords[0]], zoom_start=12, tiles="OpenStreetMap")
            
            # Overlay the Google Earth Engine NDVI tiles directly on the map
            folium.TileLayer(
                tiles=tile_url,
                attr='Google Earth Engine / Copernicus',
                name='NDVI Crop Health',
                overlay=True,
                control=True
            ).add_to(m)
            
            # Render map on the Streamlit web front-end safely
            st.success(f"Showing health metrics for {region_select}")
            folium_static(m, width=900, height=500)
            
            st.info("💡 **How to interpret:** Deep Green zones indicate dense, healthy vegetative growth. Yellow-to-Red patches indicate moisture stress, pest damage, or clear soil.")
            
        except Exception as e:
            st.error(f"No clear imagery found for this date range. Try broadening your dates. Error: {e}")
