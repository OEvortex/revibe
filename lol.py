from openai import OpenAI
import json

client = OpenAI(api_key="", base_url="https://llm.chutes.ai/v1")

models = client.models.list()
with open("model.json", "a") as f:
    for model in models.data:
        f.write(json.dumps(model.model_dump(), indent=4) + "\n")
