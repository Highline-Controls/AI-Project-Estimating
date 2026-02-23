import base64
import os
from dotenv import load_dotenv
from openai import OpenAI

# Create a file with the Files API
def create_file(pdf_path: str) -> None:
    # Loading PDF image
    with open(pdf_path, "rb") as pdf_file:
        b64_pdf = base64.b64encode(pdf_file.read()).decode('utf-8')

    with open(pdf_path, "rb") as pdf_file:
        result = client.files.create(
            file=pdf_file,
            purpose="user_data"
        )
        file_id = result.id
        print(f"file id: {file_id}")
    
    with open("pdf_file_id.txt", "a") as id_file:
        id_file.write(file_id + "\n")

# Configuration
print("Loading configuration...")
load_dotenv()
OPENAI_API_KEY=os.getenv('OPENAI_API_KEY')
client = OpenAI(api_key=OPENAI_API_KEY)
pdf_path = "Mechanical Plans/Pier 17 Mechanical Plans.pdf"
create_file(pdf_path)

# Pier 17 file id: file-Ce94hhXmVM9m8EWakGSaqH