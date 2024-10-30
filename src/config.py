from pathlib import Path
from pydantic import BaseModel, Field

from .pdf_parser import PdfParserType
from .utils import yaml_load

DEFAULT_CONFIG_YAML = Path(__file__).parent.parent / "config" / "config.yaml"

class TemplateConfig(BaseModel):
    system: str = Field("", description="The system template")
    user: str = Field("", description="The user template")

class ChainConfig(BaseModel):
    engine_name: str = Field("", alias="model_name", description="The name of the model")
    template: TemplateConfig = Field(default_factory=TemplateConfig)

class ChainsConfig(BaseModel):
    summary: ChainConfig = Field(default_factory=ChainConfig)
    mindmap: ChainConfig = Field(default_factory=ChainConfig)
    figures: ChainConfig = Field(default_factory=ChainConfig)
    insert_figures: ChainConfig = Field(default_factory=ChainConfig)

class AppConfig(BaseModel):
    engine_name: str = Field("gpt-4o-mini", alias="model_name")
    lang: str = Field("中文")
    pdf_parser: PdfParserType = Field(PdfParserType.PYMUPDF)
    debug: bool = Field(False)
    chains: ChainsConfig = Field(default_factory=ChainsConfig)

    @classmethod
    def create(cls, filename: Path = None) -> "AppConfig":
        if filename is None:
            filename = DEFAULT_CONFIG_YAML
        return cls(**yaml_load(filename))
