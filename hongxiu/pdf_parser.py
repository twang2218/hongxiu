from enum import Enum
from pathlib import Path

from loguru import logger
from pydantic import BaseModel

from .utils import check_set_gpu


class PdfParserType(Enum):
    PYMUPDF = "pymupdf"
    PYPDF2 = "pypdf2"
    PIX2TEXT = "pix2text"

    @classmethod
    def from_string(cls, s: str) -> "PdfParserType":
        try:
            return getattr(cls, s.upper())
        except AttributeError:
            raise ValueError(f"Unknown PDF parser: {s}")


class PdfParser(BaseModel):
    type: PdfParserType

    def read_pdf(self, filename: str, override: bool = True) -> str:
        raise NotImplementedError

    def get_type(self) -> PdfParserType:
        return self.type

    @classmethod
    def create(cls, type: PdfParserType = PdfParserType.PYMUPDF) -> "PdfParser":
        if type == PdfParserType.PYMUPDF:
            return PdfParserPymupdf(type=type)
        elif type == PdfParserType.PYPDF2:
            return PdfParserPypdf2(type=type)
        elif type == PdfParserType.PIX2TEXT:
            return PdfParserPix2Text(type=type)
        else:
            raise ValueError(f"Unknown PDF parser: {type}")


class PdfParserPymupdf(PdfParser):
    type: PdfParserType = PdfParserType.PYMUPDF

    def read_pdf(self, filename: str, override: bool = True) -> str:
        return read_pdf_pymupdf(filename, override=override)


class PdfParserPypdf2(PdfParser):
    type: PdfParserType = PdfParserType.PYPDF2

    def read_pdf(self, filename: str, override: bool = True) -> str:
        return read_pdf_pypdf2(filename, override=override)


class PdfParserPix2Text(PdfParser):
    type: PdfParserType = PdfParserType.PIX2TEXT

    def read_pdf(self, filename: str, override: bool = True) -> str:
        return read_pdf_pix2text(filename, override=override)


def read_pdf_pymupdf(filename: str, override: bool = True) -> str:
    try:
        # 将PDF转换为Markdown
        from pymupdf4llm import to_markdown  # type: ignore

        po = Path(filename)
        p_md = po.parent / (po.stem + ".md")
        if p_md.exists() and not override:
            logger.debug(f"File {p_md} exists, return its content")
            return p_md.read_text()
        logger.info(f"read_pdf_pymupdf(): Parsing PDF {filename}...")
        text = to_markdown(filename)
        p_md.write_text(text)
        return text
    except ImportError as e:
        logger.error("Please install pymupdf4llm, e.g., pip install pymupdf4llm")
        raise e


def read_pdf_pypdf2(filename: str, override: bool = True) -> str:
    try:
        from PyPDF2 import PdfFileReader  # type: ignore

        po = Path(filename)
        p_md = po.parent / (po.stem + ".md")
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


def read_pdf_pix2text(filename: str, override: bool = True) -> str:
    try:
        from pix2text import Pix2Text  # type: ignore

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
        doc = p2t.recognize_pdf(
            filename, table_as_image=True, text_contain_formula=False
        )
        doc.to_markdown(p_md_dir)
        text = (p_md_dir / "output.md").read_text()
        return text
    except ImportError as e:
        logger.error("Please install pix2text, e.g., pip install pix2text")
        raise e


def read_pdf(
    filename: str,
    pdf_parser: PdfParserType = PdfParserType.PYMUPDF,
    override: bool = True,
) -> str:
    if pdf_parser == PdfParserType.PYMUPDF:
        return read_pdf_pymupdf(filename, override=override)
    elif pdf_parser == PdfParserType.PYPDF2:
        return read_pdf_pypdf2(filename, override=override)
    elif pdf_parser == PdfParserType.PIX2TEXT:
        return read_pdf_pix2text(filename, override=override)
    else:
        raise ValueError(f"Unknown PDF parser: {pdf_parser}")
