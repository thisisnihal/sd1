import ee

# Initialize GEE (Replace with your GEE Project ID)
ee.Initialize(project='ecstatic-spirit-455219-c2')

def afforestation_feasibility(lat, lon):
    print("\n🌿 Fetching Sentinel-2 Land Cover Data (Updated)...")

    # Radius of 5 km (5000 meters)
    radius = 5000  

    # Filter Sentinel-2 imagery with minimal cloud cover
    s2 = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED") \
        .filterBounds(ee.Geometry.Point([lon, lat]).buffer(radius)) \
        .filterDate('2020-01-01', '2023-12-31') \
        .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 5)) \
        .select(['B8', 'B4']) \
        .median()

    # Calculate NDVI
    ndvi = s2.normalizedDifference(['B8', 'B4']).rename('NDVI')

    # Mask Green Areas (NDVI > 0.4)
    green_zone = ndvi.gt(0.4)

    # Mask Non-Green Areas (NDVI < 0.2)
    barren_zone = ndvi.lt(0.2)

    # Proximity to Green Zones (Buffer of 500m)
    green_buffer = green_zone.focal_max(radius=500, units='meters')

    # Identify Barren Land Close to Green Zones
    afforestation_area = barren_zone.And(green_buffer)

    # Generate Feasibility Report
    print("\n✅ Generating Feasibility Report...")

    try:
        # Calculate coverage percentages
        green_coverage = green_zone.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=ee.Geometry.Point([lon, lat]).buffer(radius),
            scale=30,  # 30 m scale
            maxPixels=1e9  # 1 billion pixels
        ).get('NDVI').getInfo()

        barren_coverage = barren_zone.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=ee.Geometry.Point([lon, lat]).buffer(radius),
            scale=30,  
            maxPixels=1e9
        ).get('NDVI').getInfo()

        if green_coverage is None or barren_coverage is None:
            print("\n❌ No valid land cover data available for this area.")
            return

        # Print Final Report
        print("\n🌿 Afforestation Feasibility Report:")
        print(f"- Green Cover: {green_coverage * 100:.2f}%")
        print(f"- Barren/Open Land: {barren_coverage * 100:.2f}%")

        if green_coverage > 0.2 and barren_coverage > 0.1:
            print("🌿 Afforestation is Feasible in This Area ✅")
        else:
            print("🚫 Afforestation is NOT Feasible in This Area ❌")

    except Exception as e:
        print(f"\n⚠️ Error: {e}")
        print("Try reducing the radius further or increasing the maxPixels limit.")

