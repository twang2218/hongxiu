from pathlib import Path
from pprint import pprint
import sys

import click
from loguru import logger

from .utils import download_paper, package_path
from .pdf_parser import PdfParserType
from .engine import Engine
from .config import Config


def init_logger(debug: bool):
    if debug:
        logger.remove()
        logger.add(sys.stderr, level="DEBUG")
    else:
        logger.remove()
        logger.add(sys.stderr, level="INFO")


class BaseCommand(click.core.Command):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.params.insert(
            0, click.core.Option(("--override",), is_flag=True, help="覆盖已有文件")
        )
        self.params.insert(
            0,
            click.core.Option(
                ("--model",),
                type=click.STRING,
                default=None,
                help="大语言模型，格式为 provider:model_name，例如 openai:gpt-4o-mini",
            ),
        )
        self.params.insert(
            0,
            click.core.Option(
                ("--pdf-parser",),
                type=click.Choice(["pymupdf", "pypdf2", "pix2text"]),
                default=None,
                help="PDF parser library, default is pymupdf",
            ),
        )
        self.params.insert(
            0, click.core.Option(("--debug",), is_flag=True, help="Enable debug mode")
        )
        self.params.insert(
            0,
            click.core.Option(
                ("--config",),
                type=click.Path(exists=True),
                default=None,
                help="Path to the configuration file",
            ),
        )


def init_command(config, debug, pdf_parser, model, override):
    init_logger(debug)
    # init_env_var()
    if not config:
        config = ["hongxiu.json"]
    preset_envvars = {
        "TEMPLATE_SUMMARY_PATH": package_path("config/summary.tmpl"),
        "TEMPLATE_SUMMARY_FIGURES_PATH": package_path("config/summary_figures.tmpl"),
        "TEMPLATE_SUMMARY_MERGE_FIGURES_PATH": package_path(
            "config/summary_merge_figures.tmpl"
        ),
        "TEMPLATE_MINDMAP_PATH": package_path("config/mindmap.tmpl"),
    }
    cfg = Config(
        config_files=config, prefix="HONGXIU", dotenv=True, envvars=preset_envvars
    )
    pprint(cfg.to_dict(), sort_dicts=False)
    pprint(cfg.chains.mindmap.template.system[:200] + "...")
    if pdf_parser:
        cfg.pdf_parser = PdfParserType.from_string(pdf_parser)
    if model:
        cfg.llm = model
    logger.debug(
        f"init_command(): config: {config}, debug: {debug}, pdf_parser: {pdf_parser}, override: {override}"
    )
    cfg.debug = debug
    return cfg


@click.group()
def main():
    pass


@main.command(cls=BaseCommand)
@click.argument("input_path", type=str)
@click.option("--output_dir", type=click.Path(), default=None, help="保存总结的目录")
def summary(config, debug, pdf_parser, model, override, input_path, output_dir):
    cfg = init_command(config, debug, pdf_parser, model, override)
    engine = Engine(cfg)

    pi = Path(input_path)
    if not pi.exists():
        pi = download_paper(input_path, output_dir)

    if pi.is_dir():
        inputs = [f for f in pi.iterdir() if f.suffix == ".pdf"]
    else:
        inputs = [pi]

    po = Path(output_dir) if output_dir else pi.parent
    if not po.exists():
        po.mkdir(parents=True)

    for f in inputs:
        output_filename = f.stem + ".summary.pdf"
        output_fullpath = po / output_filename
        logger.debug(f"engine.summarize(): input: {f}, output: {output_fullpath}")
        engine.summarize(f, output_fullpath, override)


@main.command(cls=BaseCommand)
@click.argument("input_path", type=str)
@click.option("--output_dir", type=click.Path(), default=None, help="保存脑图的目录")
def mindmap(config, debug, pdf_parser, model, override, input_path, output_dir):
    cfg = init_command(config, debug, pdf_parser, model, override)
    engine = Engine(cfg)

    pi = Path(input_path)
    if not pi.exists():
        paper = download_paper(input_path, output_dir)
        inputs = [paper]
    else:
        if pi.is_dir():
            inputs = [f for f in pi.iterdir() if f.suffix == ".pdf"]
        else:
            inputs = [pi]

    po = Path(output_dir) if output_dir else pi.parent
    if not po.exists():
        po.mkdir(parents=True)
    for f in inputs:
        output_pdf_filename = f.stem + ".mindmap.pdf"
        output_pdf_fullpath = po / output_pdf_filename
        logger.debug(f"engine.mindmap(): input: {f}, output: {output_pdf_fullpath}")
        engine.mindmap(f, output_pdf_fullpath, override)


@main.command(cls=BaseCommand)
@click.argument("input_path", type=click.Path(exists=True))
def dev(config, debug, pdf_parser, model, override, input_path):
    cfg = init_command(config, debug, pdf_parser, model, override)
    engine = Engine(cfg)

    pi = Path(input_path)
    po = pi.parent / pi.stem
    figures = engine.figures(input_path, output=po, override=True)
    for f in figures:
        print(f"Figure:  [{f.type}]\t{f.link}\t{f.desc}")

@main.command()
def version():
    from . import __version__
    print(f"hongxiu version: {__version__}")

if __name__ == "__main__":
    main()
