import streamlit as st
import ee
import folium
from streamlit_folium import folium_static
import datetime

# 1. Initialize Google Earth Engine using Streamlit Secrets
try:
    secret_creds = st.secrets["gcp_service_account"]
    
    # FIX: Convert literal "\n" text strings into real cryptographic line breaks
    raw_key = secret_creds["private_key"]
    clean_key = raw_key.replace("\\n", "\n")
    
    ee_creds = ee.ServiceAccountCredentials(
        secret_creds["client_email"], 
        key_data=clean_key
    )
    ee.Initialize(ee_creds)
except Exception as e:
    st.error(f"Failed to authenticate with Google Earth Engine: {e}")
    st.info("Please make sure your 'gcp_service_account' keys are filled in your Streamlit Advanced Secrets.")
    st.stop()

# Configure the Streamlit Page Layout
st.set_page_config(layout="wide")
st.title("🇪🇹 Automated NDVI Crop-Health Dashboard")
st.write("Lightweight satellite monitoring optimized for local Ethiopian administrative regions.")

# 2. Interactive Sidebar Controls
st.sidebar.header("Select Region & Date")
region_select = st.sidebar.selectbox(
    "Target Area",
    ["Oromia (Bale Zone Wheat)", "Amhara (Teff Region)", "Sidama (Coffee Zones)"]
)

# Geographic coordinates mapping for regional centers
regions = {
    "Oromia (Bale Zone Wheat)": [39.90, 7.10],
    "Amhara (Teff Region)": [37.70, 11.60],
    "Sidama (Coffee Zones)": [38.50, 6.70]
}
coords = regions[region_select]

start_date = st.sidebar.date_input("Start Date", datetime.date(2025, 9, 1))
end_date = st.sidebar.date_input("End Date", datetime.date(2026, 5, 30))

# 3. Direct Map URL Processing Pipeline
def get_ndvi_tile_url(lon, lat, start, end):
    point = ee.Geometry.Point([lon, lat])
    aoi = point.buffer(5000) # Creates a 5km cluster buffer around your centerpoint
    
    s2 = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
        .filterBounds(aoi) \
        .filterDate(start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d')) \
        .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20)) \
        .median()
        
    ndvi = s2.normalizedDifference(['B8', 'B4']).rename('NDVI')
    
    ndvi_vis = {
        'min': 0.0,
        'max': 0.8,
        'palette': ['#d73027', '#f46d43', '#fdae61', '#fee08b', '#d9ef8b', '#a6d96a', '#66bd63', '#1a9850']
    }
    
    map_id_dict = ee.Image(ndvi.clip(aoi)).getMapId(ndvi_vis)
    return map_id_dict['tile_fetcher'].url_format

# 4. Interface Rendering Trigger
if st.button("Generate Crop Health Analysis"):
    with st.spinner("Processing cloud assets from Sentinel-2..."):
        try:
            tile_url = get_ndvi_tile_url(coords[0], coords[1], start_date, end_date)
            
            m = folium.Map(location=[coords[1], coords[0]], zoom_start=12, tiles="OpenStreetMap")
            
            folium.TileLayer(
                tiles=tile_url,
                attr='Google Earth Engine / Copernicus',
                name='NDVI Crop Health',
                overlay=True,
                control=True
            ).add_to(m)
            
            st.success(f"Showing metrics for {region_select}")
            folium_static(m, width=950, height=550)
            
            st.info("💡 **Interpretation Guide:** Deep Green zones show healthy crop density. Shifting into Yellow or Red highlights areas with severe moisture deficiencies or potential pest outbreaks.")
            
        except Exception as e:
            st.error(f"Could not load telemetry maps for these parameters: {e}")
