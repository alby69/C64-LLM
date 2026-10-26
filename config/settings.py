import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Tuple
import yaml

@dataclass
class Settings:
    NANOGPT_REPO_PATH: Path = field(default_factory=lambda: Path("external/nanoGPT"))
    NANOGPT_DATA_DIR: Path = field(default_factory=lambda: Path("data/nanogpt_c64"))
    NANOGPT_OUTPUT_DIR: Path = field(default_factory=lambda: Path("data/models/nanogpt"))
    C64_SYSTEM_VECTORS: List[Tuple[int, int, str]] = field(
        default_factory=lambda: [
            (0x0314, 0x0315, "CINV (IRQ Vector)"),
            (0x0316, 0x0317, "CBINV (BRK Vector)"),
            (0x0318, 0x0319, "NMINV (NMI Vector)"),
            (0xFFFA, 0xFFFB, "NMI Vector (Hardware)"),
            (0xFFFC, 0xFFFD, "RESET Vector"),
            (0xFFFE, 0xFFFF, "IRQ/BRK Vector (Hardware)"),
        ]
    )

    @classmethod
    def load_from_yaml(cls, yaml_path: str = "config/agent_config.yaml") -> "Settings":
        settings_inst = cls()
        if os.path.exists(yaml_path):
            try:
                with open(yaml_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}

                nanogpt_cfg = data.get("nanogpt", {})
                if "repo_path" in nanogpt_cfg:
                    settings_inst.NANOGPT_REPO_PATH = Path(nanogpt_cfg["repo_path"])
                if "data_dir" in nanogpt_cfg:
                    settings_inst.NANOGPT_DATA_DIR = Path(nanogpt_cfg["data_dir"])
                if "output_dir" in nanogpt_cfg:
                    settings_inst.NANOGPT_OUTPUT_DIR = Path(nanogpt_cfg["output_dir"])

                if "system_vectors" in data:
                    settings_inst.C64_SYSTEM_VECTORS = [
                        (v["start"], v["end"], v["name"]) for v in data["system_vectors"]
                    ]
            except Exception as e:
                print(f"Warning: Failed to parse {yaml_path}: {e}")
        return settings_inst

settings = Settings.load_from_yaml()
