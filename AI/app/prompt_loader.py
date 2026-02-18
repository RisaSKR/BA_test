from pathlib import Path
import yaml

class PromptLoader:
    def __init__(self, base=Path(__file__).parent / "prompts"):
        self.base = Path(base)

    def load(self, filename: str) -> str:
        data = yaml.safe_load((self.base / filename).read_text(encoding="utf-8"))
        sections = []
        for key in ("persona", "policies", "behavior_rules", "style", "tool_use", "guardrails", "examples"):
            val = data.get(key)
            if not val:
                continue
            if isinstance(val, list):
                block = "\n".join([f"- {x}" for x in val])
            else:
                block = str(val)
            sections.append(f"{key.upper()}:\n{block}")
        return f"You are {data.get('name','an agent')}.\n\n" + "\n\n".join(sections)
