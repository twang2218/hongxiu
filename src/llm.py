from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser, BaseOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
# from langchain_community.llms import Tongyi
from langchain_community.chat_models.tongyi import ChatTongyi

def create_model(model_name: str) -> BaseChatModel:
    if model_name.startswith("qwen"):
        return ChatTongyi(model = model_name)
    else:
        return ChatOpenAI(model = model_name)

def create_chain(model_name: str, template: str, output_parser: BaseOutputParser = StrOutputParser()) -> ChatPromptTemplate:
    model = create_model(model_name)
    prompt = ChatPromptTemplate.from_messages([
            ("system", template),
            ("user", "{text}")
        ])
    chain = prompt | model | output_parser
    return chain