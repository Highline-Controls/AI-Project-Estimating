import json
from openai import OpenAI
from dotenv import load_dotenv
import os
import base64

# Create a file with the Files API
def create_file(pdf_path):
    # Loading PDF image
    pdf_path = "D:\\Pat\\Documents\\OneDrive\\Zhou Fam\\Consulting\\Clients\\Highline\\AI Project Bidding\\Wedgewood Permit Set - Mechanical.pdf"
    with open(pdf_path, "rb") as pdf_file:
        b64_pdf = base64.b64encode(pdf_file.read()).decode('utf-8')

    with open(pdf_path, "rb") as pdf_file:
        result = client.files.create(
            file=pdf_file,
            purpose="user_data"
        )
        file_id = result.id
        print(f"file id: {file_id}")
    
    with open("pdf_file_id.txt", "w") as id_file:
        id_file.write(file_id)

#create_file(pdf_path)

def prompt_chatgpt(prompt_text):
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
                        "file_id": "file-FLSnzYscmWHopF1DJzt8EZ"
                    }
                ]
            }
        ]
    )
    print(response.output_text)
    return response.output_text



print("Starting script...")
print("Loading configuration...")
# Configuration
load_dotenv()
OPENAI_API_KEY=os.getenv('OPENAI_API_KEY')
client = OpenAI(api_key=OPENAI_API_KEY)

# Loading prompt
# prompt_path = "D:\\Pat\\Documents\\OneDrive\\Documents\\Repos\\Highline-AI-Design-plans\\prompts\\simple.txt"
simple_qs_path = "D:\\Pat\\Documents\\OneDrive\\Documents\\Repos\\Highline-AI-Design-plans\\prompts\\simple_formatted.txt"
rtu_schedule_prompt_path = "D:\\Pat\\Documents\\OneDrive\\Documents\\Repos\\Highline-AI-Design-plans\\prompts\\RTU_schedule_chart_title.txt"
rtu_info_prompt_path = "D:\\Pat\\Documents\\OneDrive\\Documents\\Repos\\Highline-AI-Design-plans\\prompts\\RTU_info.txt"

with open(simple_qs_path, "r") as prompt_file:
    simple_qs_prompt = prompt_file.read()

with open(rtu_schedule_prompt_path, "r") as prompt_file:
    rtu_schedule_prompt = prompt_file.read()

with open(rtu_info_prompt_path, "r") as prompt_file:
    rtu_info_prompt = prompt_file.read()

# Simple question prompts
simple_qs = prompt_chatgpt(simple_qs_prompt)
simple_qs_json = json.loads(simple_qs)
print("Simple Questions Response:")
print(simple_qs_json)

with open("Final Output.txt", "w") as output_file:
    for qa in simple_qs_json["Questions_Answers"]:
        output_file.write(f"Q: {qa['Question']}\nA: {qa['Answer']}\n\n")

rtu_schedule_title = prompt_chatgpt(rtu_schedule_prompt)
rtu_info_prompt = rtu_info_prompt.replace("{RTU Schedule Table}", rtu_schedule_title)
rtu_info = prompt_chatgpt(rtu_info_prompt)
rtu_info_json = json.loads(rtu_info)
print("RTU Info Response:")
print(rtu_info_json)

with open("Final Output.txt", "a") as output_file:
    output_file.write("RTU Information:\n")
    for qa in rtu_info_json["Questions_Answers"]:
        output_file.write(f"Q: {qa['Question']}\nA: {qa['Answer']}\n\n")