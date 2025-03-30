import os
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, Query

from solar import predict_solar, SolarInput
from wind import (
    fetch_nasa_wind_data,
    fetch_osm_landuse,
    fetch_osm_infrastructure,
    fetch_existing_wind_turbines
)
from soil import calculate_water_harvesting_score

from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import markdown
from weasyprint import HTML
import uuid
import uvicorn


app = FastAPI()
os.makedirs("static/pdfs", exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")




@app.get("/")
async def root():
    return {"message": "Welcome to the Solar Energy API"}

class LocationRequest(BaseModel):
    latitude: float
    longitude: float


# Solar
@app.post("/check_solar_farm")
def check_solar_farm(input_data: SolarInput):
    f""" Predicted Solar Energy Potential
        Unit of "value" is kWh/m²
    """
    return predict_solar(input_data)



@app.post("/check_water_harvesting_score")
def check_water_harvesting_score(location: LocationRequest):
    latitude = location.latitude
    longitude = location.longitude
    return calculate_water_harvesting_score(latitude, longitude)









# Wind 


@app.post("/check_wind_farm")
def check_wind_farm(location: LocationRequest):
    latitude = location.latitude
    longitude = location.longitude
    
    wind_df = fetch_nasa_wind_data(latitude, longitude)
    if wind_df is None:
        return {"status": "error", "message": "Failed to fetch wind data"}

    avg_wind_speed = wind_df['WindSpeed'].mean()

    land_use_types = fetch_osm_landuse(latitude, longitude)
    
    infra_count = fetch_osm_infrastructure(latitude, longitude)
    
    wind_turbines = fetch_existing_wind_turbines(latitude, longitude)

    if wind_turbines and wind_turbines > 0:
        return {
            "status": "exists",
            "message": f"Wind farm already exists with {wind_turbines} turbines."
        }

    if avg_wind_speed < 3.5:
        return {
            "status": "not_feasible",
            "message": "Wind speed too low for a wind farm.",
            "avg_wind_speed": avg_wind_speed
        }

    unsuitable_land = {"residential", "industrial", "urban"}
    if land_use_types and land_use_types.intersection(unsuitable_land):
        return {
            "status": "not_feasible",
            "message": f"Land is {land_use_types} → Not suitable for wind farms."
        }

    if infra_count is None or infra_count < 5:
        return {
            "status": "not_feasible",
            "message": "No roads or power grid nearby → Wind farm not feasible."
        }

    turbine_type = "VAWT (Vertical Axis Wind Turbine)" if avg_wind_speed < 6.5 else "HAWT (Horizontal Axis Wind Turbine)"

    return {
        "status": "feasible",
        "message": "Wind farm feasible!",
        "avg_wind_speed": f"{round(avg_wind_speed, 2)} m/s",
        "recommended_turbine": turbine_type
    }






def generate_pdf(md_content: str) -> str:
    """Converts Markdown content (response from LLM) to PDF and saves it on the server."""
    
    html_content = markdown.markdown(md_content)
    
    pdf_filename = f"static/pdfs/summary_{uuid.uuid4().hex}.pdf"
    
    html = HTML(string=html_content)
    html.write_pdf(pdf_filename)
    
    return pdf_filename

from ai import get_summary



@app.post("/getall")
def get_all(location: LocationRequest):
    try:
        solar_input = {"latitude": location.latitude, "longitude": location.longitude}
        data = {
            "solar": check_solar_farm(solar_input),
            "wind": check_wind_farm(location),
            "water": check_water_harvesting_score(location),
        }

        str_data = str(data)
        summary = get_summary(str_data)

        pdf_file_path = generate_pdf(str_data)

        summary_link = f"/static/pdfs/{os.path.basename(pdf_file_path)}"
        
        return {
            "data": data,
            "summary_link": summary_link,
            "summary": summary
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
