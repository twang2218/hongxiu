import os
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_community.chat_models import ChatTongyi
from portkey_ai import createHeaders, PORTKEY_GATEWAY_URL

from .config import TemplateConfig

def create_model(model_name: str) -> BaseChatModel:
    if model_name.startswith("qwen"):
        m = ChatTongyi(model = model_name)
    else:
        if os.environ.get("PORTKEY_API_KEY") is not None:
            # https://portkey.ai/docs/integrations/libraries/langchain-python
            portkey_headers = createHeaders(api_key=os.environ.get("PORTKEY_API_KEY"), provider="openai")
            m = ChatOpenAI(model = model_name, base_url=PORTKEY_GATEWAY_URL, default_headers=portkey_headers)
        else:
            m = ChatOpenAI(model = model_name)
    return m

def create_chain(model_name: str, template: TemplateConfig, cls: type) -> ChatPromptTemplate:
                #  output_parser: BaseOutputParser = StrOutputParser()) -> ChatPromptTemplate:
    model = create_model(model_name)
    prompt_system = template.system.replace("{", "{{").replace("}", "}}")
    prompt_user = template.user
    # 设置 chain 的返回类型解析
    if model_name.startswith("gpt-"):
        model = model.with_structured_output(cls)
        prompt = ChatPromptTemplate.from_messages([
            ("system", prompt_system),
            ("user", prompt_user),
        ])
        chain = prompt | model
    else:
        parser = PydanticOutputParser(pydantic_object=cls)
        prompt = ChatPromptTemplate.from_messages([
            ("system", prompt_system + "\n\n{format_instructions}"),
            ("user", prompt_user),
        ]).partial(format_instructions=parser.get_format_instructions())
        chain = prompt | model | parser
    return chain
