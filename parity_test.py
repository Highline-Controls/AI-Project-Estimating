import json
from main import checksum_two, checksum_three

def test_matching_responses():
    with open("testing/base_response.json", "r") as f:
        response1 = json.load(f)
    with open("testing/matching_response.json", "r") as f:
        response2 = json.load(f)
    # print(response1["Questions_Answers"])
    test_response = checksum_two(response1, response2)

    assert test_response == response1

def test_nonmatching_responses():
    with open("testing/base_response.json", "r") as f:
        response1 = json.load(f)
    with open("testing/1_error_response.json", "r") as f:
        response2 = json.load(f)
    with open("testing/matching_response.json", "r") as f:
        new_response = json.load(f)
    test_response = checksum_three(response1, response2, new_response)

    assert test_response == response1

if __name__ == "__main__":
    test_matching_responses()
    test_nonmatching_responses()