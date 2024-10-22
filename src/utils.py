from datetime import datetime
import os
from pathlib import Path
import re
import sys
import click
from PyPDF2 import PdfReader  # 假设你使用的PDF处理库
# 需要load_dotenv来加载API_KEY
from dotenv import load_dotenv
# 配置文件使用yaml格式
from loguru import logger
import yaml
# 导入langchain_core中的相关模块
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_community.llms import Tongyi
from langchain_community.chat_models.tongyi import ChatTongyi

class Model:
    def __init__(self, model_name):
        self.model_name = model_name
        if model_name.startswith("qwen"):
            self.model = ChatTongyi(model = model_name)
        else:
            self.model = ChatOpenAI(model = model_name)
    def chain(self, template):
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", template),
                ("user", "{text}")
            ]
        )
        return prompt | self.model | StrOutputParser()

def read_pdf(filename: str) -> str:
    with open(filename, 'rb') as f:
        reader = PdfReader(f)
        text = ''
        for page in reader.pages:
            text += page.extract_text()
    return text

CONFIG_FILE = "config.yaml"
CONFIG_PROMPTS = "prompts.yaml"

def load_config(filename: str):
    with open(filename, mode='r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
        return config

def default_config_path():
    pf = Path(__file__).parent
    return pf.parent / "config" / CONFIG_FILE

def load_prompts():
    return load_config(CONFIG_PROMPTS)

def download_paper(paper: str, output_dir: str) -> Path:
    import requests
    re_arxiv = re.compile(r"\d+\.\d+")  # arXiv ID
    if paper.startswith("http"):
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
        output_dir = os.getcwd()
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
    with open(paper_path, 'wb') as f:
        f.write(r.content)
    return paper_path