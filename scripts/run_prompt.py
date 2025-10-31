import requests, json, sys

prompt = "sleek red micro spaceship, ~16 studs long, <150 parts"
if len(sys.argv) > 1:
    prompt = " ".join(sys.argv[1:])

resp = requests.post("http://127.0.0.1:8000/from_prompt", json={"prompt": prompt, "seed": 42})
print(json.dumps(resp.json(), indent=2))
