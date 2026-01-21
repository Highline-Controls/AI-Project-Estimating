from openai import OpenAI
from dotenv import load_dotenv
import os
import base64


print("Starting script...")
print("Loading configuration...")
# Configuration
load_dotenv()
OPENAI_API_KEY=os.getenv('OPENAI_API_KEY')
client = OpenAI(api_key=OPENAI_API_KEY)

# Loading prompt
# prompt_path = "D:\\Pat\\Documents\\OneDrive\\Documents\\Repos\\Highline-AI-Design-plans\\prompts\\simple.txt"
# prompt_path = "D:\\Pat\\Documents\\OneDrive\\Documents\\Repos\\Highline-AI-Design-plans\\prompts\\simple_formatted.txt"
prompt_path = "D:\\Pat\\Documents\\OneDrive\\Documents\\Repos\\Highline-AI-Design-plans\\prompts\\RTU_schedule_chart_title.txt"
with open(prompt_path, "r") as prompt_file:
    prompt_text = prompt_file.read()

# Loading PDF image
pdf_path = "D:\\Pat\\Documents\\OneDrive\\Zhou Fam\\Consulting\\Clients\\Highline\\AI Project Bidding\\Wedgewood Permit Set - Mechanical.pdf"
with open(pdf_path, "rb") as pdf_file:
    b64_pdf = base64.b64encode(pdf_file.read()).decode('utf-8')
 
# Sending request to OpenAI
print("Sending request to OpenAI...")
response = client.responses.create(
    model="gpt-5",
    input = [
        {
            "role": "user",
            "content": [
                {   "type": "input_text", "text": prompt_text },
                {
                    "type": "input_file",
                    "filename": "Wedgewood Permit Set - Mechanical.pdf",
                    "file_data": f"data:application/pdf;base64,{b64_pdf}"
                }
            ]
        }
    ]
)

print(response.output_text)