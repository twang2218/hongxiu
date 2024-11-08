from pydantic import BaseModel, Field


# 论文图片
class Figure(BaseModel):
    link: str
    type: str
    desc: str


class Figures(BaseModel):
    figures: list[Figure]


class Metadata(BaseModel):
    title: str = Field(default="", description="论文标题")
    authors: str = Field(default="", description="作者")
    institution: str = Field(default="", description="机构")
    date: str = Field(default="", description="论文日期")
    tldr: str = Field(default="", description="一句话摘要")


# 论文总结
class Summary(BaseModel):
    metadata: Metadata = Field(default=Metadata(), description="论文元数据")
    summary: dict = Field(default={}, description="论文总结")


# 思维导图
class Mindmap(BaseModel):
    metadata: Metadata = Field(default=Metadata(), description="论文元数据")
    mindmap: dict = Field(default={}, description="思维导图")
