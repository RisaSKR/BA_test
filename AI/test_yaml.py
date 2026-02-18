import yaml
from pathlib import Path

p = Path(r"c:\Users\sirisa\BA\AI\app\prompts\brands\mizumi\instruction.yaml")
try:
    with open(p, "r", encoding="utf-8") as f:
        yaml.safe_load(f)
    print("YAML is valid")
except Exception as e:
    print(f"YAML Error: {e}")
