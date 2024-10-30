from pathlib import Path
import sys
import click
from dotenv import load_dotenv
from loguru import logger
from pydantic import BaseModel

from .utils import download_paper
from .pdf_parser import PdfParserType
from .engine import Engine
from .config import AppConfig


class Context(BaseModel):
    config: AppConfig
    engine: Engine


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
                ("--pdf-parser",),
                type=click.Choice(["pymupdf", "pypdf2", "pix2text"]),
                default="pymupdf",
                help="PDF parser",
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


def init_command(config, debug, pdf_parser, override):
    init_logger(debug)
    load_dotenv()
    cfg = AppConfig.create(config)
    cfg.pdf_parser = PdfParserType.from_string(pdf_parser)
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
def summary(config, debug, pdf_parser, override, input_path, output_dir):
    cfg = init_command(config, debug, pdf_parser, override)
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
        output_filename = f.stem + ".summary.pdf"
        output_fullpath = po / output_filename
        logger.debug(f"engine.summarize(): input: {f}, output: {output_fullpath}")
        engine.summarize(f, output_fullpath, override)


@main.command(cls=BaseCommand)
@click.argument("input_path", type=str)
@click.option("--output_dir", type=click.Path(), default=None, help="保存脑图的目录")
def mindmap(config, debug, pdf_parser, override, input_path, output_dir):
    cfg = init_command(config, debug, pdf_parser, override)
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
def dev(config, debug, pdf_parser, override, input_path):
    cfg = init_command(config, debug, pdf_parser, override)
    engine = Engine(cfg)

    pi = Path(input_path)
    po = pi.parent / pi.stem
    figures = engine.figures(input_path, output=po, override=True)
    for f in figures:
        print(f"Figure:  [{f.type}]\t{f.link}\t{f.desc}")


if __name__ == "__main__":
    main()
