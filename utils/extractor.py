# Data Extraction from PDF and Giving it to LLM

import pdfplumber
import json
import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from .prompts import JOB_DESCRIPTION_PROMPT, RESUME_PROMPT

load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=api_key, temperature=0.0)

def extract_text_from_pdf(uploaded_file):
    try:
        text = ""
        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                extracted_text = page.extract_text() or ""
                if extracted_text:
                    text += extracted_text + "\n"
        return text
    except Exception as e:
        print("PDF Extraction Error: ",e)
        return ""
    

def extract_data_with_gemini(text, type="resume", job_description_data=None):
    if type=="job_description":
        final_prompt = JOB_DESCRIPTION_PROMPT.format(text=text)
    else:
        if job_description_data:
            if isinstance(job_description_data, dict):
                job_json_str = json.dumps(job_description_data, indent=2)
            else:
                job_json_str = str(job_description_data)
        else:
            job_json_str = "{}"
        final_prompt = RESUME_PROMPT.format(text=text, job_json=job_json_str)

    try:
        response = llm.invoke(final_prompt)
        content = response.content

        content = content.replace("```json", "").replace("```", "").strip()
        data = json.loads(content)
        
        return data
    
    except json.JSONDecodeError:
        print("Error: Gemini did not give a valid json")
        return None
    except Exception as e:
        print(f"General Error: {e}")
        return None