from pydantic import BaseModel, Field


# 论文图片
class Figure(BaseModel):
    link: str
    type: str
    desc: str


class Figures(BaseModel):
    figures: list[Figure]


class Metadata(BaseModel):
    title: str = Field("", description="论文标题")
    authors: str = Field("", description="作者")
    institution: str = Field("", description="机构")
    date: str = Field("", description="论文日期")
    tldr: str = Field("", description="一句话摘要")


# 论文总结
class Summary(BaseModel):
    metadata: Metadata
    summary: dict


# 思维导图
class Mindmap(BaseModel):
    metadata: Metadata
    mindmap: dict
