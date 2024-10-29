import os
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser, BaseOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
# from langchain_community.llms import Tongyi
from langchain_community.chat_models.tongyi import ChatTongyi
from portkey_ai import createHeaders, PORTKEY_GATEWAY_URL

def create_model(model_name: str) -> BaseChatModel:
    if model_name.startswith("qwen"):
        portkey_headers = createHeaders(api_key=os.environ.get("PORTKEY_API_KEY"), provider="openai")
        return ChatTongyi(model = model_name, base_url=PORTKEY_GATEWAY_URL, default_headers=portkey_headers)
    else:
        # https://portkey.ai/docs/integrations/libraries/langchain-python
        portkey_headers = createHeaders(api_key=os.environ.get("PORTKEY_API_KEY"), provider="openai")
        return ChatOpenAI(model = model_name, base_url=PORTKEY_GATEWAY_URL, default_headers=portkey_headers)

def create_chain(model_name: str, template: str, output_parser: BaseOutputParser = StrOutputParser()) -> ChatPromptTemplate:
    model = create_model(model_name)
    # print("== model_name ==:", model_name)
    # print("== template ==:\n", template)
    prompt = ChatPromptTemplate.from_messages([
            ("user", template),
            # ("user", "{text}")
        ])
    chain = prompt | model | output_parser
    return chain
