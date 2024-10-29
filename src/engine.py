from pathlib import Path
from typing import Optional, Dict, List, Callable
from loguru import logger
from pydantic import BaseModel

# 导入langchain_core中的相关模块
from langchain_core.runnables.base import RunnableSequence
from langchain.output_parsers import YamlOutputParser

from .config import AppConfig
from .llm import create_chain
from .model import Figure, Figures, Summary, Mindmap
from .pdf_parser import PdfParser, PdfParserType
from .render import render_mindmap_to_pdf, render_summary_to_latex
from .utils import latex_to_pdf, yaml_dump, yaml_load


class Engine(BaseModel):
    hooks: Dict[str, List[Callable]] = {
        "on_summary": [],
        "on_mindmap": [],
    }
    config: AppConfig = AppConfig()
    summary_chain: Optional[RunnableSequence] = None
    mindmap_chain: Optional[RunnableSequence] = None
    figures_chain: Optional[RunnableSequence] = None
    insert_figures_chain: Optional[RunnableSequence] = None
    pdf_parser: PdfParser = None

    # pylint: disable=no-member
    def __init__(self, config: dict | AppConfig, **kwargs):
        super().__init__(**kwargs)
        # 整理配置
        if isinstance(config, dict):
            self.config = AppConfig(**config)
        else:
            self.config = config
        # 初始化链
        logger.debug(f"Lang: {self.config.lang}")
        self.summary_chain = create_chain(
            self.config.chains.summary.engine_name if self.config.chains.summary.engine_name else self.config.engine_name,
            self.config.chains.summary.template.replace("{lang}", self.config.lang),
            output_parser=YamlOutputParser(pydantic_object=Summary)
        )
        self.mindmap_chain = create_chain(
            self.config.chains.mindmap.engine_name if self.config.chains.mindmap.engine_name else self.config.engine_name,
            self.config.chains.mindmap.template.replace("{lang}", self.config.lang),
            output_parser=YamlOutputParser(pydantic_object=Mindmap)
        )
        self.figures_chain = create_chain(
            self.config.chains.figures.engine_name if self.config.chains.figures.engine_name else self.config.engine_name,
            self.config.chains.figures.template.replace("{lang}", self.config.lang),
            output_parser=YamlOutputParser(pydantic_object=Figures)
        )
        self.insert_figures_chain = create_chain(
            self.config.chains.insert_figures.engine_name if self.config.chains.insert_figures.engine_name else self.config.engine_name,
            self.config.chains.insert_figures.template.replace("{lang}", self.config.lang),
            output_parser=YamlOutputParser(pydantic_object=Summary)
        )
        # 初始化PDF解析器
        self.pdf_parser = PdfParser.create(self.config.pdf_parser)

    def summarize(self, content: str|Path, output: str, override: bool = False) -> Summary:
        po = Path(output)
        p_yaml = po.parent / (po.stem + '.yaml')
        p_latex = po.parent / (po.stem + '.tex')
        p_pdf = po.parent / (po.stem + '.pdf')

        # 如果content是Path对象，说明其内不是文本内容，因此需要读取PDF文件
        if isinstance(content, Path) and content.suffix == ".pdf":
            content = self.pdf_parser.read_pdf(content, override=override)

        # 调用模型生成总结
        if p_yaml.exists() and not override:
            logger.debug(f"File {p_yaml} exists, return its content")
            summary = Summary(**yaml_load(p_yaml))
        else:
            logger.info(f"Generating Summary ({p_yaml})")
            summary = self.summary_chain.invoke({'text': content})

        # 如果pdf_parser是pix2text，则有机会抽取图片，此时我们调用 figures() 方法获取图片信息
        figures_path = []
        if self.pdf_parser.get_type() == PdfParserType.PIX2TEXT:
            # 从 Markdown 中提取重要图片
            logger.info("Extracting Figures..")
            figures = self.figures_chain.invoke({'text': content})
            # if isinstance(figures, Figures):
            #     figures = figures.figures
            # 修订图片路径，使其相对于 .tex 文件
            print(f"cwd: {Path.cwd()}, output: {output}")
            p_figures_dir = Path(output).parent / po.stem.rstrip(".summary")
            p_figures_dir = p_figures_dir.relative_to(p_latex.parent)
            figures.figures = [figure for figure in figures.figures if figure.type == "FIGURE"]
            figures_existed = []
            for figure in figures.figures:
                if not figure.link:
                    continue
                p_figure = p_figures_dir / figure.link
                p_figure_abs = p_latex.parent / p_figure
                if p_figure_abs.exists():
                    figure.link = str(p_figure)
                    figures_existed.append(figure)
                    print(f"figure.link: {figure.link}")
            figures.figures = figures_existed

            if len(figures.figures) > 0:
                # 重新生成 YAML 内容
                figures_yaml = yaml_dump(figures)
                summary_yaml = yaml_dump(summary)
                # 结合 summary 和 figures 生成新的 summary
                logger.info("Inserting Figures into Summary...")
                print(f"figures_yaml: \n{figures_yaml}")
                print(f"summary_yaml: \n{summary_yaml}")
                summary = self.insert_figures_chain.invoke({'summary': summary_yaml, 'figures': figures_yaml})
                print(f"new summary: \n{yaml_dump(summary)}")
                p_summary_figures = p_yaml.parent / (p_yaml.stem + ".figures.yaml")
                with open(p_summary_figures, 'w', encoding='utf-8') as f:
                    f.write(yaml_dump(summary))

        # 调用钩子函数
        if self.hooks["on_summary"]:
            for hook in self.hooks["on_summary"]:
                if callable(hook):
                    hook(summary)

        if not p_yaml.exists() or override:
            with open(p_yaml, 'w', encoding='utf-8') as f:
                f.write(yaml_dump(summary))

        render_summary_to_latex(summary, p_latex, figures=figures_path, override=override)
        latex_to_pdf(p_latex, p_pdf, override)
        return summary

    def figures(self, content: str|Path, output: str, override: bool = False) -> List[Figure]:
        po = Path(output)
        # p_figures_dir = po / "figures"
        # p_yaml = po / "figures.yaml"
        p_yaml = po.parent / (po.stem + '.figures.yaml')

        # 如果content是Path对象，说明其内不是文本内容，因此需要读取PDF文件
        if isinstance(content, Path) and content.suffix == ".pdf":
            content = self.pdf_parser.read_pdf(content, override=override)

        # 如果中间文件已经存在，且不覆盖，则直接返回其内容
        # if p_yaml.exists():
        #     if not override:
        #         logger.warning(f"{p_yaml} is exist, please use --override to override it.")
        #         figures = Figures(**yaml_load(p_yaml))
        #         return figures.figures
        #     else:
        #         p_yaml.unlink()

        if not po.exists():
            po.mkdir(parents=True)

        logger.info(f"Generating Figures ({p_yaml})")
        figures = self.figures_chain.invoke({'text': content})

        # with open(p_yaml, 'w', encoding='utf-8') as f:
        #     f.write(yaml_dump(figures))
        return figures.figures

    def mindmap(self, content: str|Path, output: str, override: bool = False) -> Mindmap:
        p_pdf = Path(output)
        p_yaml = p_pdf.parent / (p_pdf.stem + '.yaml')
        # p_markdown = p_pdf.parent / (p_pdf.stem + '.md')

        # 如果content是Path对象，说明其内不是文本内容，因此需要读取PDF文件
        if isinstance(content, Path) and content.suffix == ".pdf":
            content = self.pdf_parser.read_pdf(content, override=override)

        # 检查中间文件是否存在
        if p_yaml.exists():
            if not override:
                logger.warning(f"{p_yaml} is exist, please use --override to override it.")
                return Mindmap(**yaml_load(p_yaml))
            else:
                p_yaml.unlink()
    
        # 检查PDF文件是否存在
        if p_pdf.exists() and not override:
                logger.warning(f"{p_pdf} is exist, please use --override to override it.")
                return None

        # 调用模型生成脑图
        logger.info(f"Generating Mindmap YAML ({p_yaml})")
        mindmap = self.mindmap_chain.invoke({'text': content})
        with open(p_yaml, 'w', encoding='utf-8') as f:
            f.write(yaml_dump(mindmap))
        
        if self.hooks["on_mindmap"]:
            for hook in self.hooks["on_mindmap"]:
                if callable(hook):
                    hook(mindmap)

        # 转换脑图 为 PDF
        render_mindmap_to_pdf(mindmap, p_pdf, override)
    
        return mindmap

    def on_summary(self, hook: Callable):
        self.hooks["on_summary"].append(hook)
    def on_mindmap(self, hook: Callable):
        self.hooks["on_mindmap"].append(hook)
