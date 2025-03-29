import google.generativeai as genai
from fastapi import HTTPException

genai.configure(api_key="AIzaSyCgwdTBmTtSQ5vgdpCxx3N3UAt7msIaWUY") 
model = genai.GenerativeModel('gemini-1.5-flash')


global_context = """
Generate a structured sustainability report with a table for this data with proper format.
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

        
