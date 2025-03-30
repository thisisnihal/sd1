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








from fastapi import HTTPException

from typing import Dict, Union

def calculate_afforestation_feasibility(lat: float, lon: float) -> Dict[str, Union[str, bool]]:
    """
    Calculate afforestation feasibility based on land cover analysis.
    
    Args:
        lat: Latitude coordinate (float)
        lon: Longitude coordinate (float)
        
    Returns:
        Dictionary containing:
        - green_coverage: Percentage of green cover as string
        - barren_coverage: Percentage of barren land as string
        - is_feasible: Boolean feasibility result
        - status: Success/error status
        - message: Additional information
    """
    try:
        print("\n🌿 Fetching Sentinel-2 Land Cover Data (Updated)...")
        radius = 5000  # 5km radius

        # Original processing logic
        s2 = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED") \
            .filterBounds(ee.Geometry.Point([lon, lat]).buffer(radius)) \
            .filterDate('2020-01-01', '2023-12-31') \
            .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 5)) \
            .select(['B8', 'B4']) \
            .median()

        ndvi = s2.normalizedDifference(['B8', 'B4']).rename('NDVI')
        green_zone = ndvi.gt(0.4)
        barren_zone = ndvi.lt(0.2)
        green_buffer = green_zone.focal_max(radius=500, units='meters')
        afforestation_area = barren_zone.And(green_buffer)

        # Get coverage data
        green_coverage = green_zone.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=ee.Geometry.Point([lon, lat]).buffer(radius),
            scale=30,
            maxPixels=1e9
        ).get('NDVI').getInfo()

        barren_coverage = barren_zone.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=ee.Geometry.Point([lon, lat]).buffer(radius),
            scale=30,
            maxPixels=1e9
        ).get('NDVI').getInfo()

        if green_coverage is None or barren_coverage is None:
            return {
                "status": "error",
                "message": "No valid land cover data available",
                "green_coverage": "0.00",
                "barren_coverage": "0.00",
                "is_feasible": False
            }

        # Calculate results
        is_feasible = green_coverage > 0.2 and barren_coverage > 0.1
        
        return {
            "status": "success",
            "message": "Analysis completed successfully",
            "green_coverage": f"{green_coverage * 100:.2f}",
            "barren_coverage": f"{barren_coverage * 100:.2f}",
            "is_feasible": is_feasible,
            "feasibility_criteria": {
                "required_green": ">20%",
                "required_barren": ">10%"
            }
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "green_coverage": "0.00",
            "barren_coverage": "0.00",
            "is_feasible": False,
            "suggestion": "Try reducing the analysis radius"
        }