from datetime import datetime
import os
from pathlib import Path
import sys
import click
from PyPDF2 import PdfReader  # 假设你使用的PDF处理库
# 需要load_dotenv来加载API_KEY
from dotenv import load_dotenv
# 配置文件使用yaml格式
import yaml
# 导入langchain_core中的相关模块
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_community.llms import Tongyi
from langchain_community.chat_models.tongyi import ChatTongyi
# 导入difflib模块，用于比较修改前后的文本差异
import difflib

class Logger:
    '''
    定义一个日志类，用以记录小说生成相关内容到文件
    '''
    def __init__(self, filename="history.md", basedir=""):
        # 如果未指定basedir，则默认使用当前日期作为basedir
        if not basedir:
            basedir = datetime.now().strftime("%Y-%m-%d")
        # 检查basedir是否存在，不存在则创建，存在则创建一个新的basedir
        for i in range(100):
            d = basedir if i == 0 else f"{basedir}_{i}"
            if not os.path.exists(d):
                os.makedirs(d)
                self.basedir = d
                break
        self.filename = filename
        # 拼接文件路径
        self.fullpath = os.path.join(self.basedir, self.filename)
        # 清空文件
        with open(self.fullpath, 'w', encoding='utf-8') as f:
            f.write('')
    def log(self, message):
        '''
        写入日志
        '''
        # 对于markdown标题，需要在前后加上换行符
        if message.startswith('#'):
            message = '\n' + message + '\n'
        # 对于过长的消息，命令行只输出前200字
        if len(message) > 200:
            print(message[:200], '...', f'({len(message)}  字)')
        else:
            print(message)
        # 写入文件
        with open(self.fullpath, 'a', encoding='utf-8') as f:
            f.write(message + '\n')
    def write(self, filename, content):
        '''
        写入文件
        '''
        with open(os.path.join(self.basedir, filename), 'w', encoding='utf-8') as f:
            f.write(content)

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
