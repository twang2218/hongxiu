from pathlib import Path
import re
from typing import Optional, Dict, List, Callable
from loguru import logger
from pydantic import BaseModel
# 导入langchain_core中的相关模块
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser, BaseOutputParser
from langchain.output_parsers import YamlOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables.base import RunnableSequence
from langchain_openai import ChatOpenAI
from langchain_community.llms import Tongyi
from langchain_community.chat_models.tongyi import ChatTongyi
import yaml

from .render import render_markdown, render_latex, latex_to_pdf
from .config import AppConfig, load_template
from .md2mm import markdown_to_mindmap

def create_model(model_name: str) -> BaseChatModel:
    if model_name.startswith("qwen"):
        return ChatTongyi(model = model_name)
    else:
        return ChatOpenAI(model = model_name)

def create_chain(model_name: str, template: str, output_parser: BaseOutputParser = StrOutputParser()) -> ChatPromptTemplate:
    model = create_model(model_name)
    prompt = ChatPromptTemplate.from_messages([
            ("system", template),
            ("user", "{text}")
        ])
    chain = prompt | model | output_parser
    return chain

def remove_markdown_wrapper(content: str) -> str:
    re_markdown_wrapper = re.compile(r"```\w*\n(.+)\n```", re.RegexFlag.S)
    m = re_markdown_wrapper.match(content)
    if m:
        # 发现内容被markdown包裹，提取其中的内容
        return m.group(1)
    else:
        # 直接返回原内容
        return content
    

class Figure(BaseModel):
    link: str
    type: str
    desc: str

class Figures(BaseModel):
    figures: List[Figure]

class Engine(BaseModel):
    hooks: Dict[str, List[Callable]] = {
        "on_summary": [],
        "on_mindmap_markdown": [],
        "on_mindmap_pdf": []
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
            self.config.chains.summary.template
        )
        self.mindmap_chain = create_chain(
            self.config.chains.mindmap.engine_name,
            self.config.chains.mindmap.template,
        )
        self.figures_chain = create_chain(
            self.config.chains.figures.engine_name,
            self.config.chains.figures.template,
            output_parser=YamlOutputParser(pydantic_object=Figures)
        )

    def summarize(self, content: str, output: str, override: bool = False) -> str:
        po = Path(output)
        p_yaml = po.parent / (po.stem + '.yaml')
        p_md = po.parent / (po.stem + '.md')
        p_latex = po.parent / (po.stem + '.tex')
        p_pdf = po.parent / (po.stem + '.pdf')

        # 如果文件已经存在，且不覆盖，则直接返回.md文件内容
        if p_yaml.exists() and False:
            summary = p_yaml.read_text(encoding='utf-8')
        else:
            logger.info(f"Generating Summary to {p_yaml}")
            summary = self.summary_chain.invoke({'text': content})
            summary = remove_markdown_wrapper(summary)

        # 调用钩子函数
        if self.hooks["on_summary"]:
            for hook in self.hooks["on_summary"]:
                if callable(hook):
                    hook(summary)

        if override:
            with open(p_yaml, 'w', encoding='utf-8') as f:
                f.write(summary)

        render_markdown(summary, p_md, override)
        template = load_template()
        render_latex(summary, template, p_latex, override)
        latex_to_pdf(p_latex, p_pdf, override)
        return summary

    def figures(self, content: str, output: str, override: bool = False) -> List[Figure]:
        po = Path(output)
        p_figures_dir = po / "figures"
        p_yaml = po / "figures.yaml"

        # 如果文件已经存在，且不覆盖，则直接返回.md文件内容
        if p_yaml.exists():
            if not override:
                logger.warning(f"{p_figures_dir} is exist, please use --override to override it.")
                return p_yaml.read_text(encoding='utf-8')
            else:
                p_yaml.unlink()

        if not po.exists():
            po.mkdir(parents=True)

        logger.info(f"Generating Figures to {p_yaml}")
        figures = self.figures_chain.invoke({'text': content})
        with open(p_yaml, 'w', encoding='utf-8') as f:
            f.write(yaml.dump(figures.dict(), default_flow_style=False, allow_unicode=True))
        return figures.figures

    def mindmap(self, content: str, output: str, override: bool = False) -> str:
        # 检查是否已经存在脑图Markdown文件
        po = Path(output)
        markdown_file = po.parent / (po.stem + '.md')

        markdown = None
        # 如果文件已经存在，且不覆盖，则直接返回.md文件内容
        if not override and markdown_file.exists():
            markdown = markdown_file.read_text(encoding='utf-8')
            if po.exists():
                logger.warning(f"{output} is exist, please use --override to override it.")
                return markdown
        
        if not markdown:
            # 调用模型生成脑图 Markdown
            logger.info(f"Generating Mindmap Markdown to {markdown_file}")
            markdown = self.mindmap_chain.invoke({'text': content})
            # 清理返回结果，去除无关内容
            re_markdown_wrapper = re.compile(r"```markdown\n(.+)\n```", re.RegexFlag.S)
            m = re_markdown_wrapper.match(markdown)
            if m:
                # 发现内容被markdown包裹，提取其中的内容
                markdown = m.group(1)
        
        with open(markdown_file, 'w', encoding='utf-8') as f:
            f.write(markdown)

        if self.hooks["on_mindmap_markdown"]:
            for hook in self.hooks["on_mindmap_markdown"]:
                if callable(hook):
                    hook(markdown)

        # 转换脑图 Markdown 为 PDF
        logger.info(f"Converting Mindmap Markdown to PDF {output}")
        markdown_to_mindmap(markdown, output)
    
        if self.hooks["on_mindmap_pdf"]:
            for hook in self.hooks["on_mindmap_pdf"]:
                if callable(hook):
                    hook(output)
    
        return markdown

    def on_summary(self, hook: Callable):
        self.hooks["on_summary"].append(hook)
    def on_mindmap_markdown(self, hook: Callable):
        self.hooks["on_mindmap_markdown"].append(hook)
    def on_mindmap_pdf(self, hook: Callable):
        self.hooks["on_mindmap_pdf"].append(hook)
