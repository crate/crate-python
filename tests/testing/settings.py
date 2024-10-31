from pathlib import Path


def crate_path() -> str:
    return str(project_root() / "parts" / "crate")


def project_root() -> Path:
    return Path(__file__).parent.parent.parent
