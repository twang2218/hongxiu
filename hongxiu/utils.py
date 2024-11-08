import os
from pathlib import Path
import re
import struct
from typing import Tuple

from loguru import logger


def download_paper(paper: str, output_dir: str) -> Path:
    import requests

    re_arxiv = re.compile(r"\d+\.\d+")  # arXiv ID
    if paper.startswith("http") or paper.startswith("https"):
        url = paper
    elif paper.lower().startswith("arXiv:"):
        id = paper.split(":")[1]
        url = f"https://arxiv.org/pdf/{id}.pdf"
    elif re_arxiv.match(paper):
        m = re_arxiv.match(paper)
        id = m.group()
        url = f"https://arxiv.org/pdf/{id}.pdf"
    else:
        logger.error(f"Unknown paper location: {paper}")

    if output_dir is None:
        output_dir = Path.cwd() / "output"
    po = Path(output_dir)
    if not po.exists():
        po.mkdir(parents=True)
    purl = Path(url)
    paper_path = po / purl.name
    # 检查是否已经下载
    if paper_path.exists():
        logger.info(f"Paper already downloaded: {paper_path}")
        return paper_path
    # 下载
    logger.info(f"Downloading paper from {url} to {paper_path}")
    r = requests.get(url)
    with open(paper_path, "wb") as f:
        f.write(r.content)
    return paper_path


def latex_to_pdf(latex_file: Path, output: Path, override: bool = False):
    if not override and output.exists():
        logger.warning(f"{output} is exist, please use --override to override it.")
        return

    logger.info(f"Converting {latex_file} to {output}")
    # 由于xelatex直接生成到当前目录，所以需要切换到输出目录
    current_dir = os.getcwd()
    os.chdir(output.parent)
    latex_file = latex_file.relative_to(output.parent)
    os.system(f"xelatex --shell-escape -interaction=batchmode {latex_file}")
    # 清理临时文件
    os.system(
        f"rm -f {latex_file.stem}.aux {latex_file.stem}.log {latex_file.stem}.out"
    )
    os.chdir(current_dir)


def hex_to_rgba(hex_color: str) -> Tuple[int, int, int, int]:
    hex_color = hex_color.lstrip("#")
    if len(hex_color) < 6:
        raise ValueError("Invalid hex color")
    elif len(hex_color) == 6:
        hex_color += "FF"

    r, g, b, a = struct.unpack("BBBB", bytes.fromhex(hex_color))
    return r, g, b, a


def color_luminance(hex_color: str) -> float:
    r, g, b, a = hex_to_rgba(hex_color)
    # REC 709
    return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255


def color_gradient(color_from: str, color_to: str, percentage: float) -> str:
    r1, g1, b1, a1 = hex_to_rgba(color_from)
    r2, g2, b2, a2 = hex_to_rgba(color_to)
    r = int(r1 + (r2 - r1) * percentage)
    g = int(g1 + (g2 - g1) * percentage)
    b = int(b1 + (b2 - b1) * percentage)
    a = int(a1 + (a2 - a1) * percentage)
    return f"#{r:02X}{g:02X}{b:02X}{a:02X}"


def check_set_gpu(override=None):
    try:
        import torch

        if override is None:
            if torch.cuda.is_available():
                device = torch.device("cuda")
                print(f"Using GPU: {torch.cuda.get_device_name(0)}")
            elif torch.backends.mps.is_available():
                device = torch.device("mps")
                print(f"Using MPS: {torch.backends.mps.is_available()}")
            else:
                device = torch.device("cpu")
                print(f"Using CPU: {torch.device('cpu')}")
        else:
            device = torch.device(override)
        return device
    except ImportError as e:
        logger.error("Please install pytorch, e.g., pip install torch")
        raise e


def ensure_list(value, cls: type = None) -> list:
    if isinstance(value, str):
        value = [value]
    elif isinstance(value, list):
        value = value
    elif isinstance(value, tuple):
        value = list(value)
    elif isinstance(value, set):
        value = list(value)
    elif isinstance(value, dict):
        value = list(value.values())
    else:
        logger.warning(f"Unknown type: {type(value)}")
        value = [value]
    if cls:
        value = [cls(i) for i in value]
    return value
