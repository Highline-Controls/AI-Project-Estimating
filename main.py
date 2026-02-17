import json
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv
import os
import base64
from prompt import Prompt
import logging
from datetime import datetime

# logfile helper
def setup_logger():
    os.makedirs("logs", exist_ok=True)

    run_ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_path = f"logs/run_{run_ts}.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler()  #for printing to terminal
        ]
    )

    logging.info("Log file created at %s", log_path)
    return log_path

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
        logging.info(f"file id: {file_id}")
    
    with open("pdf_file_id.txt", "w") as id_file:
        id_file.write(file_id)


def prompt_chatgpt(prompt: Prompt) -> str:
    res_obj_str = json.dumps(prompt.res)
    questions = ''
    # Format questions in response object
    for qa in prompt.res:
        questions = '\n' + qa['Question']

    # Build Prompt
    prompt_text = prompt.text.replace('{Questions}', questions)
    full_prompt = prompt_text + '\n' + res_obj_str

    # Sending request to OpenAI
    logging.info("Sending request to ChatGPT...")
    response = client.responses.create(
        model = MODEL,
        input = [
            {
                "role": "user",
                "content": [
                    {   "type": "input_text", "text": full_prompt },
                    {
                        "type": "input_file",
                        "file_id": FILE_ID
                    }
                ]
            }
        ]
    )

    chat_res = response.output_text
    logging.info(f"ChatGPT response: {chat_res}")
    return chat_res

def checksum_two(response1: list, response2: list) -> tuple:
    logging.info("Starting checksum_two...")

    verified_qa = []
    mismatch_qa = []

    for qa1 in response1:
        for qa2 in response2:
            if qa1['Question'] == qa2['Question'] and qa1['Answer'] == qa2['Answer']:
                # If the question and answer match in both responses, add to verified_qa
                logging.info("[CHECKSUM_TWO] Verified: %s -> %s", qa1["Question"], qa1["Answer"])
                verified_qa.append(qa1)
                break
        # If no matching QA is found in response2, add to mismatch_qa
        else:
            logging.info("[CHECKSUM_TWO] Mismatch: %s -> %s", qa1["Question"], qa1["Answer"])
            mismatch_qa.append(qa1)

    return verified_qa, mismatch_qa

# TODO: Need to handle situation where all 3 respones are different. This only works when the probability of accuracy
# is very high, otherwise it can easily get the wrong answer. In particular, math, like adding up the RTU CFM has low accuracy.
def checksum_three(response1: list, response2: list, new_response: list) -> list:
    logging.info("[CHECKSUM_THREE] tie-breaker compare")
    verified_qa = []
    for new_qa in new_response:
        for qa1 in response1:
            if new_qa['Question'] == qa1['Question'] and new_qa['Answer'] == qa1['Answer']:
                logging.info("[CHECKSUM_THREE] Match with Response 1: %s -> %s", new_qa["Question"], new_qa["Answer"])
                verified_qa.append(new_qa)
                continue
        else:
            for qa2 in response2:
                if new_qa['Question'] == qa2['Question'] and new_qa['Answer'] == qa2['Answer']:
                    logging.info("[CHECKSUM_THREE] Match with Response 2: %s -> %s", new_qa["Question"], new_qa["Answer"])
                    verified_qa.append(new_qa)
                    continue
        logging.info("[CHECKSUM_THREE] No match: %s -> %s", new_qa["Question"], new_qa["Answer"])
    return verified_qa

def chatgpt_checksum(prompt: Prompt) -> list:
    logging.info("=== CHECKSUM START ===")

    # first call
    logging.info("[CALL 1] prompt_chatgpt -> response1")
    response1 = json.loads(prompt_chatgpt(prompt))

    # second call
    logging.info("[CALL 2] prompt_chatgpt -> response2")
    response2 = json.loads(prompt_chatgpt(prompt))

    with open("validation/checksum_comparison.txt", "w") as comparison_file:
        comparison_file.write("Response 1:\n")
        comparison_file.write(json.dumps(response1, indent=4))
        comparison_file.write("\n\nResponse 2:\n")
        comparison_file.write(json.dumps(response2, indent=4))

    verified_qa, mismatch_qa = checksum_two(response1, response2)

    if len(mismatch_qa) > 0:
        logging.info("[CHECKSUM_TWO] Found %d mismatched QAs -> running checksum_three", len(mismatch_qa))

        prompt_mismatch = Prompt(prompt.text, mismatch_qa)

        logging.info("[CALL 3] prompt_chatgpt -> response3 (mismatch-only)")
        raw3 = prompt_chatgpt(prompt_mismatch)
        logging.info("[CALL 3 OUTPUT] %s", raw3)
        new_response = json.loads(raw3)

        verified_qa += checksum_three(response1, response2, new_response)
    return verified_qa

def load_simple_prompts() -> Prompt:
    logging.info("Executing simple prompts...")

    prompt_dir = os.path.join("prompts", "simple")

    simple_qs_path = os.path.join(prompt_dir, "simple_formatted.txt")
    simple_qs_json_path = os.path.join(prompt_dir,"simple_formatted.json")

    with open(simple_qs_path, "r") as file:
        simple_qs_prompt = file.read()
    
    with open(simple_qs_json_path, "r") as file:
        simple_qs_res = json.loads(file.read())

    return Prompt(simple_qs_prompt, simple_qs_res)

def load_multistep_prompts() -> list[list]:
    logging.info("Executing multistep prompts...")

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
                logging.info(f"Warning: JSON file {json_path} does not exist for prompt {txt}")
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
    log_path = setup_logger()
    logging.info("Starting script...")

    # Configuration
    logging.info("Loading configuration...")
    load_dotenv()
    OPENAI_API_KEY=os.getenv('OPENAI_API_KEY')
    FILE_ID=os.getenv('FILE_ID')
    MODEL=os.getenv('MODEL')
    logging.info(f"Configuration loaded: MODEL={MODEL}")
    client = OpenAI(api_key=OPENAI_API_KEY)

    # pdf_path = "Wedgewood Permit Set - Mechanical.pdf"
    # create_file(pdf_path)

    # Loading prompt

    # Simple question prompts
    simple_prompts = load_simple_prompts()
    verified_qs = chatgpt_checksum(simple_prompts)
    # simple_qs_json = json.loads(verified_qs)
    # print("Simple Questions Response:")
    # print(verified_qs)

    with open("Final Output.txt", "w") as output_file:
        for qa in verified_qs:
            output_file.write(f"Q: {qa['Question']}\nA: {qa['Answer']}\n\n")

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

    logging.info("Multistep Questions Response:")
    logging.info(multistep_QAs)
    with open("Final Output.txt", "a") as output_file:
        for prompt_chain in multistep_QAs:
            logging.info(f"prompt_chain: {prompt_chain}")
            for qa in prompt_chain:
                logging.info(f"qa: {qa}")
                output_file.write(f"Q: {qa['Question']}\nA: {qa['Answer']}\n\n")