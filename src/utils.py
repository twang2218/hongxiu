import os
from pathlib import Path
import re
# 配置文件使用yaml格式
from loguru import logger

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
