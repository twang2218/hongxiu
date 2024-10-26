from pathlib import Path
from pydantic import BaseModel, Field

from .utils import yaml_load

DEFAULT_CONFIG_YAML = Path(__file__).parent.parent / "config" / "config.yaml"

class ChainConfig(BaseModel):
    engine_name: str = Field("", alias="model_name", description="The name of the model")
    template: str = Field("", description="The template used by the chain")
    class Config:
        protected_namespaces = ()

class ChainsConfig(BaseModel):
    summary: ChainConfig = Field(default_factory=ChainConfig)
    mindmap: ChainConfig = Field(default_factory=ChainConfig)
    figures: ChainConfig = Field(default_factory=ChainConfig)

class AppConfig(BaseModel):
    chains: ChainsConfig = Field(default_factory=ChainsConfig)
    debug: bool = Field(False)

    @classmethod
    def create(cls, filename: Path = None) -> "AppConfig":
        if filename is None:
            filename = DEFAULT_CONFIG_YAML
        return cls(**yaml_load(filename))
