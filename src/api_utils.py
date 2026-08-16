import yaml
import requests
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
API_CONFIG_PATH = PROJECT_ROOT / "configs" / "api_config.yaml"


def get_polyhaven_session():
    with open(API_CONFIG_PATH) as f:
        config = yaml.safe_load(f)

    session = requests.Session()
    session.headers.update({
        "User-Agent": config["polyhaven"]["user_agent"]
    })
    return session, config["polyhaven"]["base_url"]