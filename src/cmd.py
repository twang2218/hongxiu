import os
from pathlib import Path
import click
from dotenv import load_dotenv
from pydantic import BaseModel

from .utils import read_pdf, default_config_path, load_config
from .engine import Engine

# class Context:
#     def __init__(self, config):
#         self.config = config
#         self.engine = Engine(config)
class Context(BaseModel):
    config: dict
    engine: Engine

# 顶层命令
@click.group()
@click.option('--config', type=click.Path(exists=True), default=default_config_path(), help='Path to the configuration file')
@click.pass_context
def main(ctx, config):
    load_dotenv()
    cfg = load_config(config)
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
    print(f"output_dir: {output_dir}, po: {po}")
    for f in inputs:
        content = read_pdf(f)
        output_pdf_filename = f.stem + '.mindmap.pdf'
        output_pdf_fullpath = po / output_pdf_filename
        print(f"engine.mindmap(): input: {f}, output: {output_pdf_fullpath}")
        ctx.obj.engine.mindmap(content, output_pdf_fullpath, override)

# dev子命令
@main.command()
@click.argument('input_path', type=click.Path(exists=True))
@click.pass_context
def dev(ctx, input_path):
    from .md2mm import parse_markdown_to_tree
    with open(input_path, 'r', encoding='utf-8') as f:
        markdown = f.read()
        print(f"dev(): markdown: {markdown[:100]}...")
        t = parse_markdown_to_tree(markdown)
        t.print_tree()


if __name__ == '__main__':
    main()
