import json
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv
import os
import base64
from prompt import Prompt

# Create a file with the Files API
def create_file(pdf_path: str) -> None:
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

def prompt_chatgpt(prompt: Prompt) -> str:
    res_obj_str = json.dumps(prompt.res)

    #print(type(res_obj))
    #print(res_obj)
    questions = ''
    for qa in prompt.res:
        questions = '\n' + qa['Question']

    prompt_text = prompt.text.replace('{Questions}', questions)

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
    #print(response.output_text)
    return response.output_text

def checksum_two(response1: list, response2: list) -> tuple:
    print("Starting checksum_two...")

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

    return verified_qa, mismatch_qa

def checksum_three(response1: list, response2: list, new_response: list) -> list:
    print("Starting checksum_three...")
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

def chatgpt_checksum(prompt: Prompt) -> list:
    response1 = json.loads(prompt_chatgpt(prompt))
    response2 = json.loads(prompt_chatgpt(prompt))

    # Testing: Write response1 and response2 to a file forcomparison
    with open("validation/checksum_comparison.txt", "w") as comparison_file:
        comparison_file.write("Response 1:\n")
        comparison_file.write(json.dumps(response1, indent=4))
        comparison_file.write("\n\nResponse 2:\n")
        comparison_file.write(json.dumps(response2, indent=4))

    verified_qa, mismatch_qa = checksum_two(response1, response2)

    if len(mismatch_qa) > 0:
        print(f"Found {len(mismatch_qa)} mismatched QAs. Requesting new responses from ChatGPT...")
        prompt = Prompt(prompt.text, mismatch_qa)
        new_response = json.loads(prompt_chatgpt(prompt))
        verified_qa += checksum_three(response1, response2, new_response)

    return verified_qa

def load_simple_prompts() -> Prompt:
    prompt_dir = os.path.join("prompts", "simple")

    simple_qs_path = os.path.join(prompt_dir, "simple_formatted.txt")
    simple_qs_json_path = os.path.join(prompt_dir,"simple_formatted.json")

    with open(simple_qs_path, "r") as file:
        simple_qs_prompt = file.read()
    
    with open(simple_qs_json_path, "r") as file:
        simple_qs_res = json.loads(file.read())

    return Prompt(simple_qs_prompt, simple_qs_res)

def load_multistep_prompts() -> list[list]:
    prompt_dir = os.path.join("prompts", "multistep")

    multistep_prompts = []
    p = Path(prompt_dir)

    # Each dir represents a multistep prompt chain
    for dir in p.iterdir():
        uniq_prompts = dir.glob("*.txt")
        prompt_chain = []
        for txt in uniq_prompts:
            json_path = txt.with_suffix('.json')
            if not json_path.exists():
                print(f"Warning: JSON file {json_path} does not exist for prompt {txt}")
            with open(txt, "r") as file:
                prompt_text = file.read()
            with open(json_path, "r") as file:
                prompt_json = json.loads(file.read())
            order = prompt_json['order']
            prompt_chain.append({"order": order, "prompt": Prompt(prompt_text, prompt_json['res_obj'])})
            prompt_chain.sort(key=lambda x: x["order"])
        multistep_prompts.append(prompt_chain)
    return multistep_prompts

if __name__ == "__main__":
    print("Starting script...")

    # Configuration
    print("Loading configuration...")
    load_dotenv()
    OPENAI_API_KEY=os.getenv('OPENAI_API_KEY')
    client = OpenAI(api_key=OPENAI_API_KEY)

    # Loading prompt



    # Simple question prompts
    # simple_prompts = load_simple_prompts()
    # verified_qs = chatgpt_checksum(simple_prompts)
    # simple_qs_json = json.loads(verified_qs)
    # print("Simple Questions Response:")
    # print(verified_qs)

    # with open("Final Output.txt", "w") as output_file:
    #     for qa in verified_qs:
    #         output_file.write(f"Q: {qa['Question']}\nA: {qa['Answer']}\n\n")

    # Multistep Prompt
    multistep_prompts = load_multistep_prompts()
    multistep_QAs = []

    for prompt_chain in multistep_prompts:
        answer = ''
        while len(prompt_chain) > 0:
            current_prompt = prompt_chain.pop(0)
            current_prompt = current_prompt["prompt"]
            if answer != '' and type(answer) == list:
                current_prompt.text = current_prompt.text.replace("{prev_answer}", answer[0]['Answer'])
            answer = chatgpt_checksum(current_prompt)
            multistep_QAs.append(answer)

    print("Multistep Questions Response:")
    print(multistep_QAs)
    with open("Final Output.txt", "a") as output_file:
        for prompt_chain in multistep_QAs:
            print(f"prompt_chain: {prompt_chain}")
            for qa in prompt_chain:
                print(f"qa: {qa}")
                output_file.write(f"Q: {qa['Question']}\nA: {qa['Answer']}\n\n")