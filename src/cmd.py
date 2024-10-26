from pathlib import Path
import sys
import click
from dotenv import load_dotenv
from loguru import logger
from pydantic import BaseModel

from .utils import download_paper
from .pdf_parser import read_pdf
from .engine import Engine
from .config import AppConfig

class Context(BaseModel):
    config: AppConfig
    engine: Engine

def logger_init(debug: bool):
    if debug:
        logger.remove()
        logger.add(sys.stderr, level='DEBUG')
    else:
        logger.remove()
        logger.add(sys.stderr, level='INFO')

# 顶层命令
@click.group()
@click.option('--config', type=click.Path(exists=True), default=None, help='Path to the configuration file')
@click.option('--debug', is_flag=True, help='Enable debug mode')
@click.pass_context
def main(ctx, config, debug):
    logger_init(debug)
    load_dotenv()
    cfg = AppConfig.create(config)
    ctx.obj = Context(config=cfg, engine=Engine(cfg))

# summary子命令
@main.command()
@click.argument('input_path', type=str)
@click.option('--output_dir', type=click.Path(), default=None, help='保存总结的目录')
@click.option('--override', is_flag=True, help='覆盖已有文件')
@click.pass_context
def summary(ctx, input_path, output_dir, override):
    pi = Path(input_path)
    if not pi.exists():
        paper = download_paper(input_path, output_dir)
        inputs = [paper]
    else:
        if pi.is_dir():
            inputs = [f for f in pi.iterdir() if f.suffix == '.pdf']
        else:
            inputs = [pi]
    
    po = Path(output_dir) if output_dir else pi.parent
    if not po.exists():
        po.mkdir(parents=True)

    for f in inputs:
        content = read_pdf(f)
        output_filename = f.stem + '.summary.md'
        output_fullpath = po / output_filename
        logger.debug(f"engine.summarize(): input: {f}, output: {output_fullpath}")
        ctx.obj.engine.summarize(content, output_fullpath, override)


# mindmap子命令
@main.command()
@click.argument('input_path', type=str)
@click.option('--output_dir', type=click.Path(), default=None, help='保存脑图的目录')
@click.option('--override', is_flag=True, help='覆盖已有文件')
@click.pass_context
def mindmap(ctx, input_path, output_dir, override):
    pi = Path(input_path)
    if not pi.exists():
        paper = download_paper(input_path, output_dir)
        inputs = [paper]
    else:
        if pi.is_dir():
            inputs = [f for f in pi.iterdir() if f.suffix == '.pdf']
        else:
            inputs = [pi]
    
    po = Path(output_dir) if output_dir else pi.parent
    if not po.exists():
        po.mkdir(parents=True)
    for f in inputs:
        content = read_pdf(f)
        output_pdf_filename = f.stem + '.mindmap.pdf'
        output_pdf_fullpath = po / output_pdf_filename
        logger.debug(f"engine.mindmap(): input: {f}, output: {output_pdf_fullpath}")
        ctx.obj.engine.mindmap(content, output_pdf_fullpath, override)

# dev子命令
@main.command()
@click.argument('input_path', type=click.Path(exists=True))
@click.pass_context
def dev(ctx, input_path):
    from .pdf_parser import PdfParserType, read_pdf
    engine = ctx.obj.engine

    pi = Path(input_path)
    po = pi.parent / pi.stem
    content = read_pdf(input_path, pdf_parser=PdfParserType.PIX2TEXT, override=True)
    figures = engine.figures(content, output=po, override=True)
    for f in figures:
        print(f"Figure:  [{f.type}]\t{f.link}\t{f.desc}")


if __name__ == '__main__':
    main()
