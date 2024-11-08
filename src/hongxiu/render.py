import io
from pathlib import Path
from typing import List

from graphviz import Digraph  # type: ignore
from loguru import logger
from pydantic import BaseModel

from .utils import color_gradient, color_luminance, package_path
from .model import Mindmap, Summary


def render_summary_to_markdown(
    data: str | dict | Summary, output: Path, override: bool = False
) -> str:
    logger.info(f"Rendering Summary to Markdown ({output})")

    # 所有 data 都转换为目标 Summary 对象
    if isinstance(data, str):
        data = Summary.model_validate_json(data)
    elif isinstance(data, dict):
        data = Summary(**data)

    # 开始渲染 Markdown
    buf = io.StringIO()
    metadata = data.metadata
    buf.write(f"# {metadata.title}\n\n")
    if metadata.authors:
        buf.write(f"**作者：** {metadata.authors}  \n")
    if metadata.date:
        buf.write(f"**日期：** {metadata.date}  \n")
    if metadata.institution:
        buf.write(f"**机构：** {metadata.institution}  \n")

    buf.write("\n")
    if metadata.tldr:
        buf.write(f"## 摘要\n\n{metadata.tldr}\n\n")

    if data.summary:
        buf.write("## 总结\n\n")
        for title in data.summary:
            buf.write(f"### {title}\n\n")
            for subtitle in data.summary[title]:
                buf.write(f"#### {subtitle}\n\n")
                if isinstance(data.summary[title][subtitle], list):
                    for item in data.summary[title][subtitle]:
                        buf.write(f"- {item}\n")
                if isinstance(data.summary[title][subtitle], dict):
                    for item in data.summary[title][subtitle]:
                        buf.write(
                            f"- **{item}:** {data.summary[title][subtitle][item]}\n"
                        )
                else:
                    buf.write(data.summary[title][subtitle])
                buf.write("\n\n")

    result = buf.getvalue()
    if not override and output.exists():
        logger.warning(f"{output} is exist, please use --override to override it.")
    else:
        with open(output, "w", encoding="utf-8") as f:
            f.write(result)

    return result


def clean_key(key: str) -> str:
    if key.startswith("(") and key.endswith(")"):
        key = key.rstrip(")").lstrip("(")
    if key.startswith("[") and key.endswith("]"):
        key = key.rstrip("]").lstrip("[")
    if key.startswith('"') and key.endswith('"'):
        key = key.rstrip('"').lstrip('"')
    return key


def render_summary_to_latex_image(image: str) -> str:
    return (
        r"""
            \begin{center}
                \includegraphics[width=0.35\textwidth]{"""
        + image
        + r"""}
            \end{center}
        """
    )


def render_summary_to_latex_text_escape(text: str) -> str:
    return text.replace("&", r"\&").replace("%", r"\%").replace("_", r"\_")


def render_summary_to_latex_text(text: str) -> str:
    text = render_summary_to_latex_text_escape(text)
    # text = render_summary_to_latex_image(text)
    return text


def render_summary_to_latex_list(buf: io.StringIO, data: list, level: int = 0):
    indent = "  " * level
    buf.write(indent + r"\begin{enumerate}" + "\n")
    for item in data:
        if isinstance(item, str):
            if item.startswith("IMAGE|"):
                buf.write(indent + render_summary_to_latex_image(item[6:]) + "\n")
            else:
                buf.write(
                    indent + r"  \item " + render_summary_to_latex_text(item) + "\n"
                )
        elif isinstance(item, list):
            render_summary_to_latex_list(buf, item, level + 1)
        elif isinstance(item, dict):
            render_summary_to_latex_dict(buf, item, level + 1)
        else:
            logger.warning(
                f"render_latex_list(): Unknown type {type(item)} : {item} in list."
            )
    buf.write(indent + r"\end{enumerate}" + "\n")


def render_summary_to_latex_dict(buf: io.StringIO, data: dict, level: int = 0):
    indent = "  " * level
    buf.write(indent + r"\begin{enumerate}" + "\n")
    for key in data:
        value = data[key]
        if isinstance(value, str):
            if key == "IMAGE":
                buf.write(indent + render_summary_to_latex_image(value) + "\n")
            else:
                buf.write(
                    indent
                    + r"  \item \textbf{"
                    + clean_key(key)
                    + r"}: "
                    + render_summary_to_latex_text(value)
                    + "\n"
                )
        elif isinstance(value, list):
            buf.write(indent + r"  \item \textbf{" + clean_key(key) + r"}:" + "\n")
            render_summary_to_latex_list(buf, value, level + 2)
        elif isinstance(value, dict):
            buf.write(indent + r"  \item \textbf{" + clean_key(key) + r"}:" + "\n")
            render_summary_to_latex_dict(buf, value, level + 2)
        else:
            logger.warning(
                f"render_latex_dict(): Unknown type {type(value)} : {value} in dict."
            )
    buf.write(indent + r"\end{enumerate}" + "\n")


def render_summary_to_latex(
    data: str | dict | Summary,
    output: Path,
    figures: List[Path] | List[str] = [],
    template_file: Path = Path(package_path("config/poster-template.tex")),
    override: bool = False,
) -> str:
    logger.info(f"Rendering Summary to LaTeX ({output})")

    # 所有 data 都转换为目标 Summary 对象
    if isinstance(data, str):
        data = Summary.model_validate_json(data)
    elif isinstance(data, dict):
        data = Summary(**data)

    # 读取模板
    template = template_file.read_text(encoding="utf-8")

    ## 标题
    buf = io.StringIO()
    metadata = data.metadata
    if metadata.title:
        buf.write(r"\title {\parbox{0.9\textwidth}{\sloppy " + metadata.title + "}}\n")
    if metadata.authors:
        buf.write(
            r"\author{\parbox{0.9\textwidth}{\sloppy " + metadata.authors + "}}\n"
        )
    if metadata.date:
        buf.write(r"\date{" + metadata.date + "}\n")
    if metadata.institution:
        buf.write(
            r"\institute{\parbox{0.9\textwidth}{\sloppy "
            + metadata.institution
            + "}}\n"
        )

    latex = template.replace("|metadata|", buf.getvalue())
    buf.close()

    ## 内容
    num_titles = len(data.summary)
    left_column = num_titles // 2

    buf = io.StringIO()
    for i, title in enumerate(data.summary.keys()):
        if i in (0, left_column):
            buf.write(r"\column{0.5}" + "\n")

        value = data.summary[title]
        buf.write(r"\block{" + title + r"}{" + "\n")
        if isinstance(value, list):
            render_summary_to_latex_list(buf, value, 1)
        elif isinstance(value, dict):
            render_summary_to_latex_dict(buf, value, 1)
        elif isinstance(value, str):
            if title == "IMAGE":
                buf.write(render_summary_to_latex_image(value) + "\n")
            else:
                buf.write(value + "\n")
        else:
            logger.warning(
                f"render_latex(): Unknown type {type(data.summary[title])} : {data.summary[title]} in summary."
            )
        buf.write("}\n")
    latex = latex.replace("|content|", buf.getvalue())

    if not override and output.exists():
        logger.warning(f"{output} is exist, please use --override to override it.")
    else:
        with open(output, "w", encoding="utf-8") as f:
            f.write(latex)

    return latex


DEFAULT_PALETTE = [
    "#000000",  # 黑色
    "#FF6F61",  # 鲜艳的珊瑚红
    "#6B5B95",  # 紫罗兰色
    "#88B04B",  # 青绿色调的黄绿色
    "#F7CAC9",  # 粉色调
    "#92A8D1",  # 浅蓝紫色
    "#F7786B",  # 鲜艳的粉红
    "#DE7A22",  # 鲜橙色
    "#2E8B57",  # 海洋绿
    "#FFD700",  # 金黄色
    "#4682B4",  # 钢蓝色
    "#D9534F",  # 鲜艳的红色
    "#5BC0DE",  # 浅蓝色
    "#FFB347",  # 橙黄色
    "#B39EB5",  # 淡紫色
    "#E94E77",  # 鲜亮的玫瑰红
]


class Style(BaseModel):
    shape: str = "rect"
    style: str = "rounded,filled"
    fill_color: str = "#FFFFFF"
    border_color: str = "#000000"
    font_color: str = "#000000"
    fontname: str = "Arial"
    fontsize: int = 12


def render_mindmap_to_dot(
    data: str | dict | Mindmap, output: Path, override: bool = False
) -> str:
    """
    由 Mindmap 对象生成 DOT 文件，然后调用 Graphviz 生成 PDF 文件
    """
    # 整理输出路径
    p_dot = output.with_suffix(".dot")
    p_pdf = output.with_suffix(".pdf")

    logger.info(f"Rendering Mindmap via GraphViz ({p_pdf})")

    # 所有 data 都转换为目标 Mindmap 对象
    if isinstance(data, str):
        data = Mindmap.model_validate_json(data)
    elif isinstance(data, dict):
        data = Mindmap(**data)

    # 开始渲染 DOT
    dot = Digraph(comment=data.metadata.title)
    dot.attr(rankdir="LR", layout="dot")
    dot.node_attr.update(
        shape="rect",
        style="rounded,filled",
        color="white",
        fontname="Arial",
        fontsize="12",
    )
    dot.edge_attr.update(
        dir="none", color="#000000", penwidth="2", headport="w", tailport="e"
    )

    palette = DEFAULT_PALETTE.copy()
    palette.reverse()

    def calculate_node_style(level: int, parent_style: Style = Style()) -> Style:
        nonlocal palette
        if level <= 1:
            # 第一级决定颜色，每个分支颜色不同
            style = parent_style.model_copy()
            current_color = palette.pop()
            style.fill_color = current_color
            style.border_color = current_color
            luma = color_luminance(current_color)
            if luma < 0.6:
                style.font_color = "#FFFFFF"
            else:
                style.font_color = "#000000"
        else:
            # 其他级别，颜色逐渐淡化
            style = parent_style.model_copy()
            current_color = color_gradient(parent_style.fill_color, "#FFFFFF", 0.5)
            style.fill_color = current_color
            style.border_color = current_color
            luma = color_luminance(current_color)
            if luma < 0.5:
                style.font_color = "#FFFFFF"
            else:
                style.font_color = "#000000"
        return style

    max_id = 0

    def dfs(
        node: str | list | dict,
        node_id: int = 0,
        node_level: int = 0,
        parent_id: int = -1,
        parent_style: Style = Style(),
    ):
        nonlocal max_id

        if isinstance(node, str):
            # 叶子节点
            node_style = calculate_node_style(node_level, parent_style)
            dot.node(
                f"node_{node_id}",
                node,
                fillcolor=node_style.fill_color,
                fontcolor=node_style.font_color,
                color=node_style.border_color,
            )
            if parent_id >= 0:
                dot.edge(
                    f"node_{parent_id}", f"node_{node_id}", color=node_style.fill_color
                )
        elif isinstance(node, list):
            # 列表节点
            for item in node:
                max_id += 1
                node_style = calculate_node_style(node_level, parent_style)
                dot.node(
                    f"node_{max_id}",
                    "",
                    fillcolor=node_style.fill_color,
                    fontcolor=node_style.font_color,
                    color=node_style.border_color,
                )
                if parent_id >= 0:
                    dot.edge(
                        f"node_{parent_id}",
                        f"node_{max_id}",
                        color=node_style.fill_color,
                    )
                dfs(item, max_id, node_level + 1, node_id, node_style)
        elif isinstance(node, dict):
            # 处理dict的每个key-value对
            for key in node:
                # 为key创建节点
                max_id += 1
                key_node_id = max_id
                node_style = calculate_node_style(node_level, parent_style)
                dot.node(
                    f"node_{key_node_id}",
                    key,
                    fillcolor=node_style.fill_color,
                    fontcolor=node_style.font_color,
                    color=node_style.border_color,
                )
                if parent_id >= 0:
                    dot.edge(
                        f"node_{parent_id}",
                        f"node_{key_node_id}",
                        color=node_style.fill_color,
                    )

                # 递归处理value,使用新的节点id
                max_id += 1
                dfs(node[key], max_id, node_level + 1, key_node_id, node_style)
        else:
            logger.warning(f"dfs(): Unknown type {type(node)} : {node} in mindmap.")

    # root
    root = {data.metadata.title: data.mindmap}
    dfs(root, 0, 0)

    # 输出
    logger.debug(f"render_mindmap_to_dot(): dot: {p_dot}, pdf: {p_pdf}")
    dot.render(p_dot, format="pdf", outfile=p_pdf)
    return dot.source


def render_mindmap_to_pdf(
    data: str | dict | Mindmap, output: Path, override: bool = False
) -> str:
    dot = render_mindmap_to_dot(data, output.with_suffix(".dot"), override)
    return dot
