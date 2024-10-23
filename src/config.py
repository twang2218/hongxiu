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

def get_file_path(filename: str) -> Path:
    return Path(__file__).parent.parent / "config" / filename

CONFIG_FILE = "config.yaml"
LATEX_TEMPLATE_FILE = "poster-template.tex"

DEFAULT_CONFIG_YAML = get_file_path(CONFIG_FILE)
DEFAULT_LATEX_TEMPLATE = get_file_path(LATEX_TEMPLATE_FILE)

def load_config(filename: str = DEFAULT_CONFIG_YAML) -> AppConfig:
    with open(filename, mode='r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
        appcfg = AppConfig(**config)
        return appcfg

def load_template(filename: str = DEFAULT_LATEX_TEMPLATE) -> str:
    with open(filename, mode='r', encoding='utf-8') as f:
        return f.read()