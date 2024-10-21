from pathlib import Path
import sys
import click
from dotenv import load_dotenv
from loguru import logger
from pydantic import BaseModel

from .utils import read_pdf
from .engine import Engine
from .config import AppConfig, load_config, DEFAULT_CONFIG_YAML

class Context(BaseModel):
    config: AppConfig
    engine: Engine

def setup_logger(debug: bool):
    if debug:
        logger.remove()
        logger.add(sys.stderr, level='DEBUG')
    else:
        logger.remove()
        logger.add(sys.stderr, level='INFO')

# 顶层命令
@click.group()
@click.option('--config', type=click.Path(exists=True), default=DEFAULT_CONFIG_YAML, help='Path to the configuration file')
@click.option('--debug', is_flag=True, help='Enable debug mode')
@click.pass_context
def main(ctx, config, debug):
    load_dotenv()
    cfg = load_config(config)
    setup_logger(debug)
    ctx.obj = Context(config=cfg, engine=Engine(cfg))

# summary子命令
@main.command()
@click.argument('input_path', type=click.Path(exists=True))
@click.option('--output_dir', type=click.Path(), default=None, help='保存总结的目录')
@click.option('--override', is_flag=True, help='覆盖已有文件')
@click.pass_context
def summary(ctx, input_path, output_dir, override):
    pi = Path(input_path)
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
@click.argument('input_path', type=click.Path(exists=True))
@click.option('--output_dir', type=click.Path(), default=None, help='保存脑图的目录')
@click.option('--override', is_flag=True, help='覆盖已有文件')
@click.pass_context
def mindmap(ctx, input_path, output_dir, override):
    pi = Path(input_path)
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
    from .md2mm import parse_markdown_to_tree
    logger.level('TRACE')
    with open(input_path, 'r', encoding='utf-8') as f:
        markdown = f.read()
        logger.debug(f"dev(): markdown: {markdown[:100]}...")
        t = parse_markdown_to_tree(markdown)
        for node in t.dfs():
            logger.debug(node)

if __name__ == '__main__':
    main()
