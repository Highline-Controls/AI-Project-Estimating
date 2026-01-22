import json
from main import checksum_two, checksum_three

def test_matching_responses():
    response1 = json.loads(open("testing/base_response.json", "r").read())
    response2 = json.loads(open("testing/matching_response.json", "r").read())
    # print(response1["Questions_Answers"])
    test_response = checksum_two(response1, response2, "Test Prompt", {})

    assert test_response == response1

def test_nonmatching_responses():
    response1 = json.loads(open("testing/base_response.json", "r").read())
    response2 = json.loads(open("testing/1_error_response.json", "r").read())
    new_response = json.loads(open("testing/matching_response.json", "r").read())
    test_response = checksum_three(response1, response2, new_response)

    assert test_response == response1

if __name__ == "__main__":
    test_matching_responses()
    test_nonmatching_responses()