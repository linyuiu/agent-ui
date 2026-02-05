from pathlib import Path

from dotenv import load_dotenv


def _load_env() -> None:
    base_dir = Path(__file__).resolve().parents[1]
    env_path = base_dir / ".env"
    load_dotenv(env_path)


_load_env()
