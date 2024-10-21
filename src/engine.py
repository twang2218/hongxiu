from pathlib import Path
import re
from typing import Optional, Dict, List, Callable
from loguru import logger
from pydantic import BaseModel, Field
# 导入langchain_core中的相关模块
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables.base import RunnableSequence
from langchain_openai import ChatOpenAI
from langchain_community.llms import Tongyi
from langchain_community.chat_models.tongyi import ChatTongyi

from .config import AppConfig
from .md2mm import markdown_to_mindmap

def create_model(model_name: str) -> BaseChatModel:
    if model_name.startswith("qwen"):
        return ChatTongyi(model = model_name)
    else:
        return ChatOpenAI(model = model_name)

def create_chain(model_name: str, template: str) -> ChatPromptTemplate:
    model = create_model(model_name)
    prompt = ChatPromptTemplate.from_messages([
            ("system", template),
            ("user", "{text}")
        ])
    chain = prompt | model | StrOutputParser()
    return chain

class Engine(BaseModel):
    hooks: Dict[str, List[Callable]] = {
        "on_summary": [],
        "on_mindmap_markdown": [],
        "on_mindmap_pdf": []
    }
    config: AppConfig = AppConfig()
    summary_chain: Optional[RunnableSequence] = None
    mindmap_chain: Optional[RunnableSequence] = None

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
            self.config.chains.mindmap.template
        )

    def summarize(self, content: str, output: str, override: bool = False) -> str:
        summary = self.summary_chain.invoke({'text': content})
        if self.hooks["on_summary"]:
            for hook in self.hooks["on_summary"]:
                if callable(hook):
                    hook(summary)
        if override:
            with open(output, 'w', encoding='utf-8') as f:
                f.write(summary)
        else:
            if Path(output).exists():
                logger.warning(f"{output} is exist, please use --override to override it.")
        return summary

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
