import google.generativeai as genai
from fastapi import HTTPException

genai.configure(api_key="AIzaSyCgwdTBmTtSQ5vgdpCxx3N3UAt7msIaWUY") 
model = genai.GenerativeModel('gemini-1.5-flash')


global_context = """
Generate a structured sustainability report in a professional format with a table for the following data. Include a title, reporting period (use "2024" as the year), location (use "Site Assessment Area" if not specified), and detailed analysis. Format the report clearly with headings and bullet points where necessary.
Structure the report as follows:
1. **Title**: Sustainability Assessment Report  
2. **Location**: Latitude & Longitude 
3. **Executive Summary** (Brief overview of findings)  
4. **Detailed Analysis** (Breakdown of solar, wind, water, green and barren/open area feasibility in a table + explanations)  
5. **Recommendations** (Based on the data)  

Make sure to provide all important details of input json properly
Ensure no placeholder text like "[Insert...]" appears. Use exact values from the data.
### Input JSON:
"""
models = genai.list_models()
for model in models:
    print(model.name, model.supported_generation_methods)

def get_summary(data:str):
    """Fetch a summary from Gemini API"""
    try:
        global global_context
        prompt = f"{global_context}\n{data}"
        models = genai.list_models()
        print("data = ", data)
        model = genai.GenerativeModel("gemini-1.5-pro")
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
         raise HTTPException(status_code=500, detail=f"Gemini API error: {str(e)}")

        
