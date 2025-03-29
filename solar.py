from typing import Dict, Optional
import requests
import pickle
import pandas as pd
import os
from sklearn.ensemble import RandomForestRegressor
from pydantic import BaseModel

# Caching
solar_data_cache: Dict[str, pd.DataFrame] = {}  # Cache for solar data per lat/lon
model_cache: Dict[str, RandomForestRegressor] = {}  # Cache models per lat/lon

NASA_API_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
MODEL_DIR = "models"
os.makedirs(MODEL_DIR, exist_ok=True)

class SolarInput(BaseModel):
    latitude: float
    longitude: float
    year: Optional[int] = 2025
    month: Optional[int] = 1

def fetch_nasa_data(lat: float, lon: float):
    cache_key = f"{lat},{lon}"
    if cache_key in solar_data_cache:
        return solar_data_cache[cache_key]
    
    params = {
        "parameters": "ALLSKY_SFC_SW_DWN",
        "community": "RE",
        "longitude": lon,
        "latitude": lat,
        "start": "20100101",
        "end": "20241231",
        "format": "JSON"
    }
    response = requests.get(NASA_API_URL, params=params)
    if response.status_code != 200:
        return None
    
    data = response.json()
    values = data['properties']['parameter']['ALLSKY_SFC_SW_DWN']
    df = pd.DataFrame(list(values.items()), columns=['Date', 'Solar_Radiation'])
    df['Date'] = pd.to_datetime(df['Date'], format='%Y%m%d')
    df['Year'] = df['Date'].dt.year
    df['Month'] = df['Date'].dt.month
    df['DayOfYear'] = df['Date'].dt.dayofyear
    df['Solar_Radiation'] = df['Solar_Radiation'].apply(lambda x: max(0, x))
    
    solar_data_cache[cache_key] = df
    return df

def get_model(lat: float, lon: float):
    cache_key = f"{lat},{lon}"
    model_path = os.path.join(MODEL_DIR, f"{cache_key}.pkl")
    
    if cache_key in model_cache:
        return model_cache[cache_key]
    
    if os.path.exists(model_path):
        with open(model_path, "rb") as f:
            model = pickle.load(f)
            model_cache[cache_key] = model
            return model
    
    df = fetch_nasa_data(lat, lon)
    if df is None:
        return None
    
    X, y = df[['Year', 'Month', 'DayOfYear']], df['Solar_Radiation']
    model = RandomForestRegressor(n_estimators=200, max_depth=10, random_state=42)
    model.fit(X, y)
    
    with open(model_path, "wb") as f:
        pickle.dump(model, f)
    
    model_cache[cache_key] = model
    return model

def predict_solar(input_data: SolarInput):
    model = get_model(input_data.latitude, input_data.longitude)
    if model is None:
        return {"message": "Failed to fetch or train model."}
    
    day_of_year = pd.Timestamp(year=input_data.year, month=input_data.month, day=15).dayofyear
    X_pred = pd.DataFrame([[input_data.year, input_data.month, day_of_year]], columns=['Year', 'Month', 'DayOfYear'])
    prediction = model.predict(X_pred)[0]
    
    if prediction > 5.0:
            recommendation = "✅ Excellent potential! Installing solar is a great investment."
    elif 3.5 <= prediction <= 5.0:
        recommendation = "👍 Good potential. Solar installation is beneficial."
    elif 2.0 <= prediction < 3.5:
        recommendation = "⚠️ Moderate potential. Consider additional analysis before installation."
    else:
        recommendation = "❌ Low potential. Solar may not be a cost-effective option."

    
    return {"value": f"{max(0, round(prediction, 3))} kWh/m²", "result": recommendation}
