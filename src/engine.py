import io
import os
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
import yaml
import yaml.parser

from .config import AppConfig, load_template
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

def remove_markdown_wrapper(content: str) -> str:
    re_markdown_wrapper = re.compile(r"```\w*\n(.+)\n```", re.RegexFlag.S)
    m = re_markdown_wrapper.match(content)
    if m:
        # 发现内容被markdown包裹，提取其中的内容
        return m.group(1)
    else:
        # 直接返回原内容
        return content
    
def render_markdown(data: str, output: Path, override: bool = False) -> str:
    logger.info(f"Rendering Markdown to {output}")
    if isinstance(data, str):
        data = yaml.safe_load(data)
    buf = io.StringIO()

    # 开始渲染 Markdown
    buf.write(f"# {data['title']}\n\n")
    if 'authors' in data:
        buf.write(f"**作者：** {data['authors']}  \n")
    if 'date' in data:
        buf.write(f"**日期：** {data['date']}  \n")
    if 'institution' in data:
        buf.write(f"**机构：** {data['institution']}  \n")

    buf.write("\n")
    if 'tldr' in data:
        buf.write(f"## 摘要\n\n{data['tldr']}\n\n")
    
    if 'summary' in data:
        buf.write("## 总结\n\n")
        for title in data['summary']:
            buf.write(f"### {title}\n\n")
            for subtitle in data['summary'][title]:
                buf.write(f"#### {subtitle}\n\n")
                if isinstance(data['summary'][title][subtitle], list):
                    for item in data['summary'][title][subtitle]:
                        buf.write(f"- {item}\n")
                if isinstance(data['summary'][title][subtitle], dict):
                    for item in data['summary'][title][subtitle]:
                        buf.write(f"- **{item}:** {data['summary'][title][subtitle][item]}\n")
                else:
                    buf.write(data['summary'][title][subtitle])
                buf.write("\n\n")

    result = buf.getvalue()
    if not override and output.exists():
        logger.warning(f"{output} is exist, please use --override to override it.")
    else:
        with open(output, 'w', encoding='utf-8') as f:
            f.write(result)

    return result

def render_latex_text_escape(text: str) -> str:
    return text.replace("&", r"\&").replace("%", r"\%").replace("_", r"\_")

def render_latex_list(buf: io.StringIO, data: list, level: int = 0):
    indent = "  " * level
    buf.write(indent + r"\begin{enumerate}" + "\n")
    for item in data:
        if isinstance(item, str):
            buf.write(indent + r"  \item " + render_latex_text_escape(item) + "\n")
        elif isinstance(item, list):
            render_latex_list(buf, item, level + 1)
        elif isinstance(item, dict):
            render_latex_dict(buf, item, level + 1)
        else:
            logger.warning(f"render_latex_list(): Unknown type {type(item)} : {item} in list.")
    buf.write(indent + r"\end{enumerate}" + "\n")

def render_latex_dict(buf: io.StringIO, data: dict, level: int = 0):
    indent = "  " * level
    buf.write(indent + r"\begin{enumerate}" + "\n")
    for key in data:
        value = data[key]
        if isinstance(value, str):
            buf.write(indent + r"  \item \textbf{" + key + r"}: " + render_latex_text_escape(value) + "\n")
        elif isinstance(value, list):
            buf.write(indent + r"  \item \textbf{" + key + r"}:" + "\n")
            render_latex_list(buf, value, level + 2)
        elif isinstance(value, dict):
            buf.write(indent + r"  \item \textbf{" + key + r"}:" + "\n")
            render_latex_dict(buf, value, level + 2)
        else:
            logger.warning(f"render_latex_dict(): Unknown type {type(value)} : {value} in dict.")
    buf.write(indent + r"\end{enumerate}" + "\n")

def render_latex(data: dict|str, template: str, output: Path, override: bool = False) -> str:
    logger.info(f"Rendering LaTeX to {output}")
    if isinstance(data, str):
        data = yaml.safe_load(data)

    ## 标题
    buf = io.StringIO()
    if 'title' in data:
        buf.write(r"\title {\parbox{0.9\textwidth}{\sloppy " + data['title'] + "}}\n")
    if 'authors' in data:
        buf.write(r"\author{\parbox{0.9\textwidth}{\sloppy " + data['authors'] + "}}\n")
    if 'date' in data:
        buf.write(r"\date{" + data['date'] + "}\n")
    if 'institution' in data:
        buf.write(r"\institute{\parbox{0.9\textwidth}{\sloppy " + data['institution'] + "}}\n")
    latex = template.replace("|metadata|", buf.getvalue())
    buf.close()

    ## 内容
    num_titles = len(data['summary'])
    left_column = num_titles // 2

    buf = io.StringIO()
    for i, title in enumerate(data['summary'].keys()):
        if i in (0, left_column):
            buf.write(r"\column{0.5}" + "\n")
        value = data['summary'][title]
        buf.write(r"\block{" + title + r"}{" + "\n")
        if isinstance(value, list):
            render_latex_list(buf, value, 1)
        elif isinstance(value, dict):
            render_latex_dict(buf, value, 1)
        elif isinstance(value, str):
            buf.write(value + "\n")
        else:
            logger.warning(f"render_latex(): Unknown type {type(data['summary'][title])} : {data['summary'][title]} in summary.")
        buf.write("}\n")
    latex = latex.replace("|content|", buf.getvalue())

    if not override and output.exists():
        logger.warning(f"{output} is exist, please use --override to override it.")
    else:
        with open(output, 'w', encoding='utf-8') as f:
            f.write(latex)

    return latex

def latex_to_pdf(latex_file: Path, output: Path, override: bool = False):
    if not override and output.exists():
        logger.warning(f"{output} is exist, please use --override to override it.")
        return

    logger.info(f"Converting {latex_file} to {output}")
    # 由于xelatex直接生成到当前目录，所以需要切换到输出目录
    current_dir = os.getcwd()
    os.chdir(output.parent)
    latex_file = latex_file.relative_to(output.parent)
    os.system(f"xelatex --shell-escape -interaction=nonstopmode {latex_file}")
    # 清理临时文件
    os.system(f"rm -f {latex_file.stem}.aux {latex_file.stem}.log {latex_file.stem}.out")  
    os.chdir(current_dir)

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
