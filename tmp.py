

import os


# AccuWeather API key and base URL
API_KEY = 'ZL4kbiQROIXMEWB5RHrjw4HUIe8cAlql'  
BASE_URL = 'http://dataservice.accuweather.com/'


class ForecastDay(BaseModel):
    date: str
    temperature_max: float
    temperature_min: float
    day_description: str
    night_description: str

class WeatherForecast(BaseModel):
    location: str
    forecast: List[ForecastDay]

# Function to get the location key for Bengaluru
@app.get('/getkey')
def get_location_key(city_name: str):
    API_KEY = 'ZL4kbiQROIXMEWB5RHrjw4HUIe8cAlql'  
    BASE_URL = 'http://dataservice.accuweather.com/'
    url = f"{BASE_URL}locations/v1/cities/search"
    params = {
        'apikey': API_KEY,
        'q': city_name
    }
    response = requests.get(url, params=params)
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="Error getting location key")
    data = response.json()
    print("data = ", data)
    return data[0]['Key'] if data else None

# Function to get 10-day weather forecast for Bengaluru
def get_10_day_forecast(location_key: str):
    API_KEY = 'ZL4kbiQROIXMEWB5RHrjw4HUIe8cAlql'  
    BASE_URL = 'http://dataservice.accuweather.com/'
    url = f"{BASE_URL}forecasts/v1/daily/10day/{location_key}"
    params = {
        'apikey': API_KEY,
        'metric': 'true'  # Use metric for temperatures in Celsius
    }
    response = requests.get(url, params=params)
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="Error getting forecast data")
    
    forecast_data = response.json()
    
    forecast = []
    for day in forecast_data['DailyForecasts']:
        forecast.append(ForecastDay(
            date=day['Date'],
            temperature_max=day['Temperature']['Maximum']['Value'],
            temperature_min=day['Temperature']['Minimum']['Value'],
            day_description=day['Day']['IconPhrase'],
            night_description=day['Night']['IconPhrase']
        ))
    
    return forecast

@app.get("/weather/forecast/{city_name}", response_model=WeatherForecast)
async def get_weather_forecast(city_name: str):
    # Step 1: Get the location key for the city
    location_key = get_location_key(city_name)
    print("location key =", location_key)
    if not location_key:
        raise HTTPException(status_code=404, detail="City not found")
    
    # Step 2: Get 10-day weather forecast
    forecast = get_10_day_forecast(location_key)
    
    return WeatherForecast(location=city_name, forecast=forecast)

