import requests
import pandas as pd

def fetch_nasa_wind_data(lat, lon, start_year=2011, end_year=2022):
    base_url = "https://power.larc.nasa.gov/api/temporal/monthly/point"
    params = {
        "parameters": "WS10M",
        "community": "RE",
        "longitude": lon,
        "latitude": lat,
        "start": start_year,
        "end": end_year,
        "format": "JSON"
    }

    response = requests.get(base_url, params=params)
    if response.status_code != 200:
        return None

    data = response.json()
    wind_speeds = data['properties']['parameter']['WS10M']
    
    df = pd.DataFrame(list(wind_speeds.items()), columns=['YearMonth', 'WindSpeed'])
    df['Year'] = df['YearMonth'].str[:4].astype(int)

    return df

def fetch_osm_landuse(lat, lon, radius=5000):
    overpass_url = "https://overpass-api.de/api/interpreter"
    query = f"""
    [out:json];
    way(around:{radius},{lat},{lon})["landuse"];
    out body;
    """
    response = requests.get(overpass_url, params={"data": query})
    
    if response.status_code != 200:
        return None

    land_use_types = set()
    for element in response.json().get("elements", []):
        if "tags" in element and "landuse" in element["tags"]:
            land_use_types.add(element["tags"]["landuse"])

    return land_use_types

def fetch_osm_infrastructure(lat, lon, radius=5000):
    overpass_url = "https://overpass-api.de/api/interpreter"
    query = f"""
    [out:json];
    (
        way(around:{radius},{lat},{lon})["highway"];
        way(around:{radius},{lat},{lon})["power"];
        way(around:{radius},{lat},{lon})["power"="line"];
    );
    out body;
    """
    response = requests.get(overpass_url, params={"data": query})
    
    if response.status_code != 200:
        return None

    return len(response.json().get("elements", []))

def fetch_existing_wind_turbines(lat, lon, radius=5000):
    overpass_url = "https://overpass-api.de/api/interpreter"
    query = f"""
    [out:json];
    node(around:{radius},{lat},{lon})["power"="generator"]["generator:source"="wind"];
    out body;
    """
    response = requests.get(overpass_url, params={"data": query})

    if response.status_code != 200:
        return None

    return len(response.json().get("elements", []))

def determine_wind_farm(lat, lon):
    wind_df = fetch_nasa_wind_data(lat, lon)
    
    if wind_df is None:
        return "❌ No wind data available."

    avg_wind_speed = wind_df['WindSpeed'].mean()

    land_use_types = fetch_osm_landuse(lat, lon)

    infra_count = fetch_osm_infrastructure(lat, lon)

    wind_turbines = fetch_existing_wind_turbines(lat, lon)

    if wind_turbines > 0:
        return f"✅ Wind farm already exists! Detected {wind_turbines} wind turbines."

    if avg_wind_speed < 3.5:
        return "❌ Wind speed too low for a wind farm."

    unsuitable_land = {"residential", "industrial", "urban"}
    if land_use_types and land_use_types.intersection(unsuitable_land):
        return f"❌ Land is {land_use_types} → Not suitable for wind farms."

    if infra_count < 5:
        return "❌ No roads or power grid nearby → Wind farm not feasible."

    if avg_wind_speed < 6.5:
        turbine_type = "VAWT (Vertical Axis Wind Turbine)"
    else:
        turbine_type = "HAWT (Horizontal Axis Wind Turbine)"

    return f"✅ Wind Farm Feasible! Recommended Turbine: {turbine_type}"
