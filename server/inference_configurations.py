from dataclasses import dataclass
from typing import Dict
from engine import CONFIG
from huggingface_hub import snapshot_download

@dataclass
class InferenceConfiguration:
    repo_id: str
    device_map: Dict = 'auto'
    max_memory: Dict[int, str] = None

    checkpoint_path: str = None


inference_configurations = [
    InferenceConfiguration(
        "gpt2"
    ),
    InferenceConfiguration(
        "decapoda-research/llama-65b-hf",
        # {
        #     0: "0GiB",
        #     1: "0GiB",
        #     2: "0GiB",
        #     3: "0GiB",
        #     4: "86GiB",
        #     5: "86GiB",
        #     6: "86GiB",
        #     7: "86GiB",
        # },
    )
]

for inference_configuration in inference_configurations:

    inference_configuration.checkpoint_path = snapshot_download(inference_configuration.repo_id, force_download=False, allow_patterns=["*.bin", "*.json", "*.model"], cache_dir=CONFIG['APP']['MODEL_CACHE_PATH'])