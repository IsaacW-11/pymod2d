from dataclasses import dataclass

@dataclass
class AssetConfig:
    root: str = "assets"
    auto_scan: bool = True
    preload: bool = False