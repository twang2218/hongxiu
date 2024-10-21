from pathlib import Path
from pydantic import BaseModel, Field
import yaml

class ChainConfig(BaseModel):
    engine_name: str = Field("", alias="model_name", description="The name of the model")
    template: str = Field("", description="The template used by the chain")
    class Config:
        protected_namespaces = ()

class ChainsConfig(BaseModel):
    summary: ChainConfig = Field(default_factory=ChainConfig)
    mindmap: ChainConfig = Field(default_factory=ChainConfig)

class AppConfig(BaseModel):
    chains: ChainsConfig = Field(default_factory=ChainsConfig)
    debug: bool = Field(False)

CONFIG_FILE = "config.yaml"

DEFAULT_CONFIG_YAML = Path(__file__).parent.parent / "config" / CONFIG_FILE

def load_config(filename: str = DEFAULT_CONFIG_YAML) -> AppConfig:
    with open(filename, mode='r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
        appcfg = AppConfig(**config)
        return appcfg
