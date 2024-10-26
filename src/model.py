from pydantic import BaseModel

# 论文图片
class Figure(BaseModel):
    link: str
    type: str
    desc: str

class Figures(BaseModel):
    figures: list[Figure]


class Metadata(BaseModel):
    title: str
    authors: str
    institution: str
    date: str
    tldr: str


# 论文总结
class Summary(BaseModel):
    metadata: Metadata
    summary: dict

# 思维导图
class Mindmap(BaseModel):
    metadata: Metadata
    mindmap: dict
