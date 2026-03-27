import yaml
from pathlib import Path

_CONFIG_PATH = Path(__file__).parent.parent / "config" / "config.yaml"


def load() -> dict:
    with open(_CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)


def save(cfg: dict):
    with open(_CONFIG_PATH, "w") as f:
        yaml.dump(cfg, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
