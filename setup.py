from setuptools import setup, find_packages

setup(
    name="hongxiu",
    version="0.1.0",
    description="A tool for converting Markdown to mindmaps and summarizing PDFs",
    author="Tao Wang",
    author_email="twang2218@gmail.com",
    url="https://github.com/twang2218/hongxiu",  # 项目的URL
    packages=find_packages(where="src"),  # 自动发现src目录下的所有包
    package_dir={"": "src"},  # 包的根目录
    include_package_data=True,  # 包含包中的所有数据文件
    install_requires=[
        "click",
        "graphviz",
        "loguru",
        "pydantic",
        "python-dotenv",
        "langchain-core",
        "langchain-openai",
        "langchain-community",
    ],
    entry_points={
        "console_scripts": [
            "hongxiu=cmd:main",  # 将命令行工具绑定到cmd.py中的main函数
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.7",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.7",
)
