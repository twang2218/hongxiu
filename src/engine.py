from pathlib import Path
from typing import Optional, Dict, List, Callable
from loguru import logger
from pydantic import BaseModel

# 导入langchain_core中的相关模块
from langchain_core.runnables.base import RunnableSequence

from .config import AppConfig
from .llm import create_chain
from .model import Figure, Figures, Summary, Mindmap
from .pdf_parser import PdfParser, PdfParserType
from .render import render_mindmap_to_pdf, render_summary_to_latex
from .utils import latex_to_pdf


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
        logger.info(f"Engine: {self.config.engine_name}")
        self.summary_chain = create_chain(
            self.config.engine_name,
            self.config.chains.summary.template,
            Summary,
        )
        self.mindmap_chain = create_chain(
            self.config.engine_name,
            self.config.chains.mindmap.template,
            Mindmap,
        )
        self.figures_chain = create_chain(
            self.config.engine_name,
            self.config.chains.figures.template,
            Figures,
        )
        self.insert_figures_chain = create_chain(
            self.config.engine_name,
            self.config.chains.insert_figures.template,
            Summary,
        )
        # 初始化PDF解析器
        self.pdf_parser = PdfParser.create(self.config.pdf_parser)

    def summarize(
        self, content: str | Path, output: str, override: bool = False
    ) -> Summary:
        po = Path(output)
        p_json = po.parent / (po.stem + ".json")
        p_latex = po.parent / (po.stem + ".tex")
        p_pdf = po.parent / (po.stem + ".pdf")

        # 如果content是Path对象，说明其内不是文本内容，因此需要读取PDF文件
        if isinstance(content, Path) and content.suffix == ".pdf":
            content = self.pdf_parser.read_pdf(content, override=override)

        # 调用模型生成总结
        if p_json.exists() and not override:
            logger.debug(f"File {p_json} exists, return its content")
            summary = Summary.model_validate_json(p_json.read_text(encoding="utf-8"))
        else:
            logger.info(f"Generating Summary ({p_json})")
            summary = self.summary_chain.invoke({"text": content})

        # 如果pdf_parser是pix2text，则有机会抽取图片，此时我们调用 figures() 方法获取图片信息
        figures_path = []
        if self.pdf_parser.get_type() == PdfParserType.PIX2TEXT:
            # 从 Markdown 中提取重要图片
            logger.info("Extracting Figures..")
            figures = self.figures_chain.invoke({"text": content})
            if figures is None:
                logger.warning("Failed to extract figures. None returned.")
            else:
                # print(f"figures: ({type(figures)}) {figures}")
                # 修订图片路径，使其相对于 .tex 文件
                print(f"cwd: {Path.cwd()}, output: {output}")
                p_figures_dir = Path(output).parent / po.stem.rstrip(".summary")
                p_figures_dir = p_figures_dir.relative_to(p_latex.parent)
                figures.figures = [
                    figure for figure in figures.figures if figure.type == "FIGURE"
                ]
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
                    # 重新生成 JSON 内容
                    figures_json = figures.model_dump_json(indent=2)
                    summary_json = summary.model_dump_json(indent=2)
                    # 结合 summary 和 figures 生成新的 summary
                    logger.info("Inserting Figures into Summary...")
                    # print(f"figures_json: \n{figures_json}")
                    # print(f"summary_json: \n{summary_json}")
                    summary_new = self.insert_figures_chain.invoke(
                        {"summary": summary_json, "figures": figures_json}
                    )
                    if summary is None:
                        logger.warning("Failed to insert figures into summary.")
                    else:
                        summary = summary_new
                        summary_json = summary.model_dump_json(indent=2)
                        # print(f"new summary: \n{summary_json}")
                        p_summary_figures = p_json.parent / (
                            p_json.stem + ".figures.json"
                        )
                        with open(p_summary_figures, "w", encoding="utf-8") as f:
                            f.write(summary_json)

        # 调用钩子函数
        if self.hooks["on_summary"]:
            for hook in self.hooks["on_summary"]:
                if callable(hook):
                    hook(summary)

        if not p_json.exists() or override:
            p_json.write_text(summary.model_dump_json(indent=2), encoding="utf-8")

        render_summary_to_latex(
            summary, p_latex, figures=figures_path, override=override
        )
        latex_to_pdf(p_latex, p_pdf, override)
        return summary

    def figures(
        self, content: str | Path, output: str, override: bool = False
    ) -> List[Figure]:
        po = Path(output)
        # p_figures_dir = po / "figures"
        # p_json = po / "figures.json"
        p_json = po.parent / (po.stem + ".figures.json")

        # 如果content是Path对象，说明其内不是文本内容，因此需要读取PDF文件
        if isinstance(content, Path) and content.suffix == ".pdf":
            content = self.pdf_parser.read_pdf(content, override=override)

        # 如果中间文件已经存在，且不覆盖，则直接返回其内容
        # if p_json.exists():
        #     if not override:
        #         logger.warning(f"{p_json} is exist, please use --override to override it.")
        #         figures = Figures.model_validate_json(p_json.read_text(encoding='utf-8'))
        #         return figures.figures
        #     else:
        #         p_json.unlink()

        if not po.exists():
            po.mkdir(parents=True)

        logger.info(f"Generating Figures ({p_json})")
        figures = self.figures_chain.invoke({"text": content})

        # p_json.write_text(figures.model_dump_json(indent=2), encoding='utf-8')
        return figures.figures

    def mindmap(
        self, content: str | Path, output: str, override: bool = False
    ) -> Mindmap:
        p_pdf = Path(output)
        p_json = p_pdf.parent / (p_pdf.stem + ".json")
        # p_markdown = p_pdf.parent / (p_pdf.stem + '.md')

        # 如果content是Path对象，说明其内不是文本内容，因此需要读取PDF文件
        if isinstance(content, Path) and content.suffix == ".pdf":
            content = self.pdf_parser.read_pdf(content, override=override)

        # 检查中间文件是否存在
        if p_json.exists():
            if not override:
                logger.warning(
                    f"{p_json} is exist, please use --override to override it."
                )
                return Mindmap.model_validate_json(p_json.read_text(encoding="utf-8"))
            else:
                p_json.unlink()

        # 检查PDF文件是否存在
        if p_pdf.exists() and not override:
            logger.warning(f"{p_pdf} is exist, please use --override to override it.")
            return None

        # 调用模型生成脑图
        logger.info(f"Generating Mindmap JSON ({p_json})")
        mindmap = self.mindmap_chain.invoke({"text": content})
        p_json.write_text(mindmap.model_dump_json(indent=2), encoding="utf-8")

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
