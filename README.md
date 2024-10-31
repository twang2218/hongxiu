<div align="center">

# 红袖 (HongXiu)

[![Python 3.7+](https://img.shields.io/badge/Python-3.7+-blue.svg)](https://www.python.org/downloads/release/python-370/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

🎯 基于AI的学术论文阅读助手 | 让阅读文献更轻松

</div>

---

## 📖 简介

红袖是一个强大的学术论文阅读辅助工具，它利用人工智能帮助研究人员和学生更好地理解学术论文，通过自动生成论文摘要和思维导图，让文献阅读变得更加高效。

## ✨ 主要功能

### 📝 论文摘要生成

自动生成全面的论文摘要，包括：
- 📌 研究背景和动机
- 🔍 研究方法和技术
- 🧪 实验设计（如果适用）
- 📊 结果分析
- 💡 结论和启示

### 🗺️ 思维导图生成

创建论文的可视化思维导图，帮助理解：
- 📑 论文结构和流程
- 🔗 关键概念和关系
- ⭐ 主要发现和结论

### 🛠️ 技术特点

- **多种PDF解析器支持**
  - ✅ PyMuPDF（默认）
  - ✅ PyPDF2
  - ✅ Pix2Text

- **专业输出格式**
  - 📄 PDF格式的论文摘要（使用LaTeX排版）
  - 🎨 PDF格式的思维导图

## 🚀 快速开始

### 📦 安装

```bash
pip install hongxiu
```

### 💻 使用方法

#### 生成论文摘要

```bash
hongxiu summary paper.pdf --output_dir ./output
```

📋 输出文件：
- `paper.summary.pdf`：格式化的摘要
- `paper.summary.json`：结构化的摘要数据
- `paper.summary.tex`：LaTeX源文件

#### 创建思维导图

```bash
hongxiu mindmap paper.pdf --output_dir ./output
```

🎯 输出文件：
- `paper.mindmap.pdf`：可视化思维导图
- `paper.mindmap.json`：结构化思维导图数据

### ⚙️ 命令选项

所有命令的通用选项：
- `--config`：自定义配置文件路径
- `--pdf-parser`：选择PDF解析器（pymupdf/pypdf2/pix2text）
- `--debug`：启用调试模式
- `--override`：覆盖现有文件

## 🔧 配置

通过JSON文件提供配置：

```json
{
  "model_name": "qwen-turbo",
  "lang": "中文",
  "pdf_parser": "pymupdf",
  "debug": false,
  "chains": {
    "summary": {
      "template": {
        "system": "...",
        "user": "..."
      }
    },
    "mindmap": {
      "template": {
        "system": "...",
        "user": "..."
      }
    },
    "figures": {
      "template": {
        "system": "...",
        "user": "..."
      }
    }
  }
}
```

## 📚 依赖项

| 依赖包 | 用途 |
|--------|------|
| click | 命令行界面 |
| graphviz | 思维导图可视化 |
| loguru | 日志记录 |
| pydantic | 数据验证 |
| python-dotenv | 环境管理 |
| langchain-core | LLM集成 |
| langchain-openai | OpenAI集成 |
| langchain-community | 社区模型支持 |

## 📄 开源协议

[MIT License](https://opensource.org/licenses/MIT)

## 👨‍💻 作者

王涛 (twang2218@gmail.com)

---

<div align="center">

**红袖** ❤️ 让研究更轻松

</div>
