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

def log_prompt(msg: str) -> None:
    with open("logs/prompts/prompt_log.log", "a", encoding="utf-8") as prompt_log:
        prompt_log.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | {msg}\n")
    return

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


def prompt_chatgpt(prompt: Prompt) -> list[dict[str, str]]:
    res_obj_str = json.dumps(prompt.res)
    questions = ''
    # Format questions in response object
    for qa in prompt.res:
        questions = '\n' + qa['Question']

    # Build Prompt
    prompt_text = prompt.text.replace('{Questions}', questions)
    full_prompt = prompt_text + '\n' + res_obj_str

    # Sending request to OpenAI
    log_prompt(full_prompt)
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

    log_prompt(f"ChatGPT response: {response.output_text}")
    try:
        chat_res = json.loads(response.output_text)
    except json.JSONDecodeError as e:
        logging.error("Error decoding ChatGPT response to JSON: %s", e)
        raise

    logging.info(f"ChatGPT response...")
    for qa in chat_res:
        logging.info(qa["Question"])
        logging.info(qa["Answer"])
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
    response1 = prompt_chatgpt(prompt)

    # second call
    logging.info("[CALL 2] prompt_chatgpt -> response2")
    response2 = prompt_chatgpt(prompt)

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
        new_response = prompt_chatgpt(prompt_mismatch)
        logging.info("[CALL 3 OUTPUT] %s", json.dumps(new_response, indent=4))

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

# Load the schedule based prompts into a list of Prompt objects
def load_schedule_prompts() -> tuple[Prompt, Prompt]:
    logging.info("Loading schedule prompts...")

    prompt_dir = os.path.join("prompts", "schedules")

    multistep_prompts = []
    p = Path(prompt_dir)

    # Each dir represents a schedule prompts
    with open(os.path.join(prompt_dir, "get_schedule_chart_titles.txt"), "r") as prompt_text:
        get_sched_text = prompt_text.read()
    with open(os.path.join(prompt_dir, "get_schedule_chart_titles.json"), "r") as prompt_res:
        get_sched_res = json.loads(prompt_res.read())
    get_sched_prompt = Prompt(get_sched_text, get_sched_res)

    with open(os.path.join(prompt_dir, "each_schedule_info.txt"), "r") as prompt_text:
        each_sched_text = prompt_text.read()
    with open(os.path.join(prompt_dir, "each_schedule_info.json"), "r") as prompt_res:
        each_sched_res = json.loads(prompt_res.read())
    each_sched_prompt = Prompt(each_sched_text, each_sched_res)
    
    return get_sched_prompt, each_sched_prompt
    
if __name__ == "__main__":
    log_path = setup_logger()
    logging.info("Starting script...")

    # Configuration
    logging.info("Loading configuration...")
    load_dotenv()
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    FILE_ID = os.getenv('FILE_ID')
    MODEL = os.getenv('MODEL') or "gpt-5-nano"  # default to gpt-5-nano if MODEL is not set
    logging.info(f"Configuration loaded: MODEL={MODEL}")
    client = OpenAI(api_key=OPENAI_API_KEY)

    # Simple question prompts
    simple_prompts = load_simple_prompts()
    verified_qs = chatgpt_checksum(simple_prompts)

    with open("Final Output.txt", "w") as output_file:
        for qa in verified_qs:
            output_file.write(f"Q: {qa['Question']}\nA: {qa['Answer']}\n\n")

    # Schedule Title Prompts
    answers = []
    get_sched_prompt, each_sched_prompt = load_schedule_prompts()
    sched_titles_res = prompt_chatgpt(get_sched_prompt)

    logging.info(f"Schedule Chart Titles: {sched_titles_res}")
    if type(sched_titles_res) == list and len(sched_titles_res) == 1:
        sched_titles =  sched_titles_res[0]
        answers.append(sched_titles)
    else:
        exception_msg = f"Unexpected format for schedule titles response: {sched_titles_res}"
        logging.error(exception_msg)
        raise ValueError(exception_msg)
    titles = sched_titles['Answer'] if 'Answer' in sched_titles else []

    #titles = titles[:3]
    if type(titles) == list:
        for title in titles:
            logging.info(f"Processing schedule: {title}")
            title_sched_prompt = each_sched_prompt.text.replace("{Schedule Title}", title)
            sched_prompt = Prompt(title_sched_prompt, each_sched_prompt.res)
            title_answers = prompt_chatgpt(sched_prompt)
            for answer in title_answers:
                logging.info(f"Answer for {title}: {answer}")
                answers.append(answer)

    logging.info("Schedule Responses:")
    logging.info(answers)
    with open("Final Output.txt", "a") as output_file:
        for qa in answers:
            logging.info(f"qa: {qa}")
            output_file.write(f"Q: {qa['Question']}\nA: {qa['Answer']}\n\n")