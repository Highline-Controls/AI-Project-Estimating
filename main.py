import json
from openai import OpenAI
from dotenv import load_dotenv
import os
import base64

# Create a file with the Files API
def create_file(pdf_path):
    # Loading PDF image
    pdf_path = "Mechanical Plans\\Wedgewood Permit Set - Mechanical.pdf"
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

def prompt_chatgpt(prompt_text, res_obj):
    res_obj_str = json.dumps(res_obj)

    # Sending request to OpenAI
    print("Sending request to OpenAI...")
    response = client.responses.create(
        model="gpt-5",
        input = [
            {
                "role": "user",
                "content": [
                    {   "type": "input_text", "text": prompt_text + '\n' + res_obj_str },
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

def checksum_two(response1, response2, prompt_text, res_obj):
    verified_qa = []
    mismatch_qa = []
    # print the type of response1
    # print(f"Type of response1: {type(response1)}")
    for qa1 in response1:
        # print(f"Type of qa1: {type(qa1)}")
        for qa2 in response2:
            if qa1['Question'] == qa2['Question'] and qa1['Answer'] == qa2['Answer']:
                # If the question and answer match in both responses, add to verified_qa
                print(f"Verified QA: {qa1['Question']} - {qa1['Answer']}")
                verified_qa.append(qa1)
                break
        # If no matching QA is found in response2, add to mismatch_qa
        else:
            print(f"Mismatch QA: {qa1['Question']} - {qa1['Answer']}")
            mismatch_qa.append(qa1)

    # if len(mismatch_qa) > 0:
    #     print(f"Found {len(mismatch_qa)} mismatched QAs.")
    #     #response3 = prompt_chatgpt(prompt_text, json.dumps(mismatch_qa))
    #     for qa3 in response3.Questions_Answers:
    #         for qa_mismatch in mismatch_qa:
    #             if qa3.Question == qa_mismatch.Question and qa3.Answer == qa_mismatch.Answer:
    #                 print(f"Updated QA: {qa3.Question} - {qa3.Answer}")
    #                 verified_qa.append(qa3)
    #                 break

    return verified_qa

def checksum_three(response1, response2, new_response):
    verified_qa = []
    for new_qa in new_response:
        for qa1 in response1:
            if new_qa['Question'] == qa1['Question'] and new_qa['Answer'] == qa1['Answer']:
                verified_qa.append(new_qa)
                break
        else:
            for qa2 in response2:
                if new_qa['Question'] == qa2['Question'] and new_qa['Answer'] == qa2['Answer']:
                    verified_qa.append(new_qa)
                    break
    return verified_qa

def chatgpt_checksum(prompt_text, res_obj):
    response1 = json.loads(prompt_chatgpt(prompt_text, res_obj))
    response2 = json.loads(prompt_chatgpt(prompt_text, res_obj))

    # Testing: Write response1 and response2 to a file forcomparison
    with open("validation/checksum_comparison.txt", "w") as comparison_file:
        comparison_file.write("Response 1:\n")
        comparison_file.write(json.dumps(response1, indent=4))
        comparison_file.write("\n\nResponse 2:\n")
        comparison_file.write(json.dumps(response2, indent=4))

    verified_qa = checksum_two(response1, response2, prompt_text, res_obj)

    return verified_qa

if __name__ == "__main__":

    print("Starting script...")
    print("Loading configuration...")
    # Configuration
    load_dotenv()
    OPENAI_API_KEY=os.getenv('OPENAI_API_KEY')
    client = OpenAI(api_key=OPENAI_API_KEY)

    # Loading prompt
    prompt_dir = "prompts/"
    # prompt_path = "D:\\Pat\\Documents\\OneDrive\\Documents\\Repos\\Highline-AI-Design-plans\\prompts\\simple.txt"
    simple_qs_path = prompt_dir + "simple_formatted.txt"
    rtu_schedule_prompt_path = prompt_dir + "RTU_schedule_chart_title.txt"
    rtu_info_prompt_path = prompt_dir + "RTU_info.txt"

    with open(simple_qs_path, "r") as prompt_file:
        simple_qs_prompt = prompt_file.read()

    with open(rtu_schedule_prompt_path, "r") as prompt_file:
        rtu_schedule_prompt = prompt_file.read()

    with open(rtu_info_prompt_path, "r") as prompt_file:
        rtu_info_prompt = prompt_file.read()

    with open("prompts/simple_formatted.json", "r") as res_file:
        simple_qs_res = json.load(res_file)

    # Simple question prompts
    verified_qs = chatgpt_checksum(simple_qs_prompt, simple_qs_res)
    simple_qs_json = json.loads(verified_qs)
    print("Simple Questions Response:")
    print(simple_qs_json)

    with open("answers/test.txt", "w") as output_file:
        for qa in simple_qs_json["Questions_Answers"]:
            output_file.write(f"Q: {qa['Question']}\nA: {qa['Answer']}\n\n")

    # rtu_schedule_title = prompt_chatgpt(rtu_schedule_prompt)
    # rtu_info_prompt = rtu_info_prompt.replace("{RTU Schedule Table}", rtu_schedule_title)
    # rtu_info = prompt_chatgpt(rtu_info_prompt)
    # rtu_info_json = json.loads(rtu_info)
    # print("RTU Info Response:")
    # print(rtu_info_json)

    # with open("Final Output.txt", "a") as output_file:
    #     output_file.write("RTU Information:\n")
    #     for qa in rtu_info_json["Questions_Answers"]:
    #         output_file.write(f"Q: {qa['Question']}\nA: {qa['Answer']}\n\n")