from pathlib import Path
import re
from typing import Optional, Dict, List, Callable
from loguru import logger
from pydantic import BaseModel

# 导入langchain_core中的相关模块
from langchain_core.runnables.base import RunnableSequence
from langchain.output_parsers import YamlOutputParser

import yaml

from .render import render_mindmap_to_pdf, render_summary_to_markdown, render_summary_to_latex
from .config import AppConfig, load_template
from .model import Figure, Figures, Summary, Mindmap
from .llm import create_chain
from .utils import latex_to_pdf, yaml_dump


class Engine(BaseModel):
    hooks: Dict[str, List[Callable]] = {
        "on_summary": [],
        "on_mindmap": [],
    }
    config: AppConfig = AppConfig()
    summary_chain: Optional[RunnableSequence] = None
    mindmap_chain: Optional[RunnableSequence] = None
    figures_chain: Optional[RunnableSequence] = None

    # pylint: disable=no-member
    def __init__(self, config: dict | AppConfig, **kwargs):
        super().__init__(**kwargs)
        if isinstance(config, dict):
            self.config = AppConfig(**config)
        else:
            self.config = config
        self.summary_chain = create_chain(
            self.config.chains.summary.engine_name,
            self.config.chains.summary.template,
            output_parser=YamlOutputParser(pydantic_object=Summary)
        )
        self.mindmap_chain = create_chain(
            self.config.chains.mindmap.engine_name,
            self.config.chains.mindmap.template,
            output_parser=YamlOutputParser(pydantic_object=Mindmap)
        )
        self.figures_chain = create_chain(
            self.config.chains.figures.engine_name,
            self.config.chains.figures.template,
            output_parser=YamlOutputParser(pydantic_object=Figures)
        )

    def summarize(self, content: str, output: str, override: bool = False) -> Summary:
        po = Path(output)
        p_yaml = po.parent / (po.stem + '.yaml')
        p_md = po.parent / (po.stem + '.md')
        p_latex = po.parent / (po.stem + '.tex')
        p_pdf = po.parent / (po.stem + '.pdf')

        # 如果文件已经存在，且不覆盖，则直接返回.md文件内容
        if p_yaml.exists() and not override:
            summary = p_yaml.read_text(encoding='utf-8')
            summary = yaml.safe_load(summary)
            summary = Summary(**summary)
        else:
            logger.info(f"Generating Summary to {p_yaml}")
            summary = self.summary_chain.invoke({'text': content})
            # summary = remove_markdown_wrapper(summary)

        # 调用钩子函数
        if self.hooks["on_summary"]:
            for hook in self.hooks["on_summary"]:
                if callable(hook):
                    hook(summary)

        if override:
            with open(p_yaml, 'w', encoding='utf-8') as f:
                f.write(yaml_dump(summary))

        render_summary_to_markdown(summary, p_md, override)
        template = load_template()
        render_summary_to_latex(summary, template, p_latex, override)
        latex_to_pdf(p_latex, p_pdf, override)
        return summary

    def figures(self, content: str, output: str, override: bool = False) -> List[Figure]:
        po = Path(output)
        p_figures_dir = po / "figures"
        p_yaml = po / "figures.yaml"

        # 如果中间文件已经存在，且不覆盖，则直接返回.md文件内容
        if p_yaml.exists():
            if not override:
                logger.warning(f"{p_figures_dir} is exist, please use --override to override it.")
                figures = Figures(**yaml.safe_load(p_yaml.read_text(encoding='utf-8')))
                return figures.figures
            else:
                p_yaml.unlink()

        if not po.exists():
            po.mkdir(parents=True)

        logger.info(f"Generating Figures to {p_yaml}")
        figures = self.figures_chain.invoke({'text': content})
        with open(p_yaml, 'w', encoding='utf-8') as f:
            f.write(yaml.dump(figures.dict(), default_flow_style=False, allow_unicode=True))
        return figures.figures

    def mindmap(self, content: str, output: str, override: bool = False) -> Mindmap:
        p_pdf = Path(output)
        p_yaml = p_pdf.parent / (p_pdf.stem + '.yaml')
        # p_markdown = p_pdf.parent / (p_pdf.stem + '.md')

        # 检查中间文件是否存在
        if p_yaml.exists():
            if not override:
                logger.warning(f"{p_yaml} is exist, please use --override to override it.")
                return Mindmap(**yaml.safe_load(p_yaml.read_text(encoding='utf-8')))
            else:
                p_yaml.unlink()
    
        # 检查PDF文件是否存在
        if p_pdf.exists() and not override:
                logger.warning(f"{p_pdf} is exist, please use --override to override it.")
                return None

        # 调用模型生成脑图
        logger.info(f"Generating Mindmap YAML to {p_yaml}")
        mindmap = self.mindmap_chain.invoke({'text': content})
        with open(p_yaml, 'w', encoding='utf-8') as f:
            f.write(yaml_dump(mindmap))
        
        if self.hooks["on_mindmap"]:
            for hook in self.hooks["on_mindmap"]:
                if callable(hook):
                    hook(mindmap)

        # 转换脑图 为 PDF
        logger.info(f"Converting Mindmap YAML to PDF {p_pdf}")
        render_mindmap_to_pdf(mindmap, p_pdf, override)
    
        return mindmap

    def on_summary(self, hook: Callable):
        self.hooks["on_summary"].append(hook)
    def on_mindmap(self, hook: Callable):
        self.hooks["on_mindmap"].append(hook)
