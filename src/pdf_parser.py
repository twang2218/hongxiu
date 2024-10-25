
from enum import Enum
from pathlib import Path

from loguru import logger

class PdfParserType(Enum):
    PYMUPDF = 1
    PYPDF2 = 2
    PIX2TEXT = 3


def check_set_gpu(override=None):
    try:
        import torch
        if override is None:
            if torch.cuda.is_available():
                device = torch.device('cuda')
                print(f"Using GPU: {torch.cuda.get_device_name(0)}")
            elif torch.backends.mps.is_available():
                device = torch.device('mps')
                print(f"Using MPS: {torch.backends.mps.is_available()}")
            else:
                device = torch.device('cpu')
                print(f"Using CPU: {torch.device('cpu')}")
        else:
            device = torch.device(override)
        return device
    except ImportError as e:
        logger.error("Please install pytorch, e.g., pip install torch")
        raise e

def read_pdf_pymupdf(filename: str, override:bool = True) -> str:
    try:
        from pymupdf4llm import to_markdown  # 将PDF转换为Markdown
        po = Path(filename)
        p_md = po.parent / (po.stem + '.md')
        if p_md.exists() and not override:
            logger.debug(f"File {p_md} exists, return its content")
            return p_md.read_text()
        logger.info(f"read_pdf_pymupdf(): Parsing PDF {filename}...")
        text = to_markdown(filename)
        p_md.write_text(text)
        return text
    except ImportError:
        logger.error("Please install pymupdf4llm, e.g., pip install pymupdf4llm")

def read_pdf_pypdf2(filename: str, override:bool = True) -> str:
    try:
        from PyPDF2 import PdfFileReader
        po = Path(filename)
        p_md = po.parent / (po.stem + '.md')
        if p_md.exists() and not override:
            logger.debug(f"File {p_md} exists, return its content")
            return p_md.read_text()
        logger.info(f"read_pdf_pypdf2(): Parsing PDF {filename}...")
        text = ""
        pdf = PdfFileReader(filename)
        for page in pdf.pages:
            text += page.extract_text() + "\n"
        p_md.write_text(text)
        return text
    except ImportError as e:
        logger.error("Please install PyPDF2, e.g., pip install PyPDF2")
        raise e

def read_pdf_pix2text(filename: str, override:bool = True) -> str:
    try:
        from pix2text import Pix2Text
        # 整理文件路径
        po = Path(filename)
        p_md_dir = po.parent / po.stem
        p_md = p_md_dir / "output.md"
        # 检查是否已经存在
        if p_md.exists() and not override:
            logger.debug(f"File {p_md} exists, return its content")
            return p_md.read_text()
        # 解析PDF
        logger.info(f"read_pdf_pix2text(): Parsing PDF {filename}...")
        p2t = Pix2Text.from_config(device=check_set_gpu())
        doc = p2t.recognize_pdf(filename, table_as_image=True, text_contain_formula=False)
        doc.to_markdown(p_md_dir)
        text = (p_md_dir / "output.md").read_text()
        return text
    except ImportError as e:
        logger.error("Please install pix2text, e.g., pip install pix2text")
        raise e

def read_pdf(filename: str, pdf_parser:PdfParserType = PdfParserType.PYMUPDF, override:bool = True) -> str:
    if pdf_parser == PdfParserType.PYMUPDF:
        return read_pdf_pymupdf(filename, override=override)
    elif pdf_parser == PdfParserType.PYPDF2:
        return read_pdf_pypdf2(filename, override=override)
    elif pdf_parser == PdfParserType.PIX2TEXT:
        return read_pdf_pix2text(filename, override=override)
    else:
        raise ValueError(f"Unknown PDF parser: {pdf_parser}")
