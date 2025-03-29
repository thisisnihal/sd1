import requests
import numpy as np
import ee

ee.Initialize(project='ecstatic-spirit-455219-c2')

def get_rainfall_score(lat, lon):
    base_url = "https://power.larc.nasa.gov/api/temporal/daily/point"
    params = {
        "parameters": "PRECTOTCORR",
        "community": "RE",
        "longitude": lon,
        "latitude": lat,
        "start": "19810101",
        "end": "20241231",
        "format": "JSON"
    }

    response = requests.get(base_url, params=params)
    if response.status_code != 200:
        return 0.0

    data = response.json()
    rainfall_values = list(data['properties']['parameter']['PRECTOTCORR'].values())

    avg_rainfall = np.sum(rainfall_values) / (2024 - 1981 + 1)
    return min(avg_rainfall / 1000, 1.0)

def get_soil_score(lat, lon):
    soil = ee.Image("OpenLandMap/SOL/SOL_TEXTURE-CLASS_USDA-TT_M/v02") \
        .select('b0') \
        .reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=ee.Geometry.Point([lon, lat]),
            scale=30
        ).get('b0').getInfo()
    
    return min(soil / 100, 1.0) if soil else 0.0

def get_slope_score(lat, lon):
    slope = ee.Terrain.slope(ee.Image("USGS/SRTMGL1_003")) \
        .reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=ee.Geometry.Point([lon, lat]),
            scale=30
        ).get('slope').getInfo()
    
    return min(slope / 45, 1.0) if slope else 0.0

def calculate_water_harvesting_score(lat, lon):
    rainfall_score = get_rainfall_score(lat, lon)
    soil_score = get_soil_score(lat, lon)
    slope_score = get_slope_score(lat, lon)

    return {
        "rainfall_score": f"{round((rainfall_score), 3)}",
        "soil_score": f"{round((soil_score), 3)}",
        "slope_score": f"{round((slope_score), 3)}",
       "water_harvesting_score": f"{round(((0.5 * rainfall_score) + (0.3 * soil_score) + (0.2 * slope_score)), 3)}"
    }
