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
from soil import calculate_water_harvesting_score, calculate_afforestation_feasibility

from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import markdown
from weasyprint import HTML
import uuid
import uvicorn


app = FastAPI()
os.makedirs("static/pdfs", exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")


from fastapi.middleware.cors import CORSMiddleware


# List of allowed IPs
allowed_ips = [
    "http://10.12.9.43:3004",
    "10.12.9.43",
    "http://10.12.10.174:3000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_ips,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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






# def generate_pdf(md_content: str) -> str:
#     """Converts Markdown content (response from LLM) to PDF and saves it on the server."""
    
#     html_content = markdown.markdown(md_content)
    
#     pdf_filename = f"static/pdfs/summary_{uuid.uuid4().hex}.pdf"
    
#     html = HTML(string=html_content)
#     html.write_pdf(pdf_filename)
    
#     return pdf_filename


import markdown2


def generate_pdf(md_content: str) -> str:
    """Converts Markdown content to PDF and saves it locally."""
    
    # Convert markdown to HTML using markdown2 with table extras
    html_content = markdown2.markdown(md_content, extras=["tables"])
    
    # Define more robust CSS for better table styling
    custom_css = """
    body {
        font-family: Arial, sans-serif;
        margin: 20px;
        line-height: 1.6;
    }
    h2, h3 {
        color: #333;
    }
    table {
        width: 100%;
        border-collapse: collapse;
        margin: 20px 0;
        page-break-inside: avoid;
    }
    th, td {
        border: 1px solid #ddd;
        padding: 8px 12px;
        text-align: left;
        vertical-align: top;
    }
    th {
        background-color: #f4f4f4;
        font-weight: bold;
    }
    tr:nth-child(even) {
        background-color: #f9f9f9;
    }
    /* Ensure tables don't overflow page width */
    table {
        word-wrap: break-word;
        table-layout: fixed;
    }
    /* Add some spacing between sections */
    h2 {
        margin-top: 30px;
    }
    """

    # Create a more robust HTML structure
    html_with_css = f"""
    <!DOCTYPE html>
    <html>
        <head>
            <meta charset="utf-8">
            <title>Sustainability Report</title>
            <style>
                {custom_css}
            </style>
        </head>
        <body>
            <div class="content">
                {html_content}
            </div>
        </body>
    </html>
    """
    
    # Create a unique PDF filename using UUID
    pdf_filename = f"static/pdfs/summary_{uuid.uuid4().hex}.pdf"
    
    # Generate the PDF with additional weasyprint options for better rendering
    html = HTML(string=html_with_css)
    html.write_pdf(
        pdf_filename,
        stylesheets=None,
        presentational_hints=True  # Helps with some table rendering
    )
    
    return pdf_filename


@app.post("/check_green")
def check_green(location: LocationRequest):
    latitude = location.latitude
    longitude = location.longitude
    return calculate_afforestation_feasibility(latitude, longitude)


from ai import get_summary



@app.post("/getall")
def get_all(location: LocationRequest):
    try:
        solar_input = SolarInput(latitude= location.latitude, longitude= location.longitude)
        data = {
            "latitude": location.latitude,
            "longitude": location.longitude,
            "solar": check_solar_farm(solar_input),
            "wind": check_wind_farm(location),
            "water": check_water_harvesting_score(location),
            "green": check_green(location)
        }

        str_data = str(data)
        summary = get_summary(str_data)

        pdf_file_path = generate_pdf(summary)

        summary_link = f"/static/pdfs/{os.path.basename(pdf_file_path)}"
        
        return {
            "data": data,
            "summary_link": summary_link,
            # "summary": summary
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
