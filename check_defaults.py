import os
os.environ["MISTRAL_API_KEY"] = "dummy"
os.environ["OPENAI_API_KEY"] = "dummy"
os.environ["HUGGINGFACE_API_KEY"] = "dummy"
os.environ["GROQ_API_KEY"] = "dummy"

from revibe.core.config import VibeConfig
from revibe.core.paths.config_paths import unlock_config_paths
unlock_config_paths()

config = VibeConfig.load()
print(f"VibeConfig.models count: {len(config.models)}")
for m in config.models:
    print(f"- {m.alias} ({m.provider})")

groq_models = [m for m in config.models if m.provider == "groq"]
print(f"Groq models in config.models: {len(groq_models)}")

