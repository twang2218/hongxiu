
import io
import os
from pathlib import Path

from loguru import logger
import yaml


def render_markdown(data: str|dict, output: Path, override: bool = False) -> str:
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
