import os
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_community.chat_models import ChatTongyi, MoonshotChat
from loguru import logger
from portkey_ai import createHeaders, PORTKEY_GATEWAY_URL

from .config import TemplateConfig


def get_extra_kwargs(provider: str = "openai") -> dict:
    # 根据配置，添加 PORTKEY 的调试网关
    if os.environ.get("PORTKEY_API_KEY") is not None:
        portkey_headers = createHeaders(
            api_key=os.environ.get("PORTKEY_API_KEY"),
            provider=provider,
        )
        return dict(
            base_url=PORTKEY_GATEWAY_URL,
            default_headers=portkey_headers,
        )
    else:
        return dict()


def create_model(provider: str, model_name: str) -> BaseChatModel:
    if provider == "openai":
        extra_kwargs = get_extra_kwargs(provider)
        m = ChatOpenAI(model=model_name, **extra_kwargs)
    elif provider == "tongyi":
        m = ChatTongyi(model=model_name)
    elif provider == "moonshot":
        m = ChatOpenAI(
            model=model_name,
            api_key=os.environ.get("MOONSHOT_API_KEY"),
            base_url="https://api.moonshot.cn/v1",
        )
        # https://github.com/langchain-ai/langchain/issues/27058
        # m = MoonshotChat(model=model_name)
    elif provider == "deepseek":
        m = ChatOpenAI(
            model=model_name,
            api_key=os.environ.get("DEEPSEEK_API_KEY"),
            base_url="https://api.deepseek.com",
        )
    elif provider == "anthropic":
        m = ChatAnthropic(model=model_name)
    return m


def create_chain(
    model_name: str, template: TemplateConfig, cls: type
) -> ChatPromptTemplate:
    if ":" not in model_name:
        logger.warning(
            f"missing provider in model name: {model_name}, using 'openai' as default"
        )
        model_name = f"openai:{model_name}"
    provider, model_name = model_name.split(":")

    model = create_model(provider, model_name)
    prompt_system = template.system.replace("{", "{{").replace("}", "}}")
    prompt_user = template.user
    # 设置 chain 的返回类型解析
    if provider in ["openai"]:
        model = model.with_structured_output(cls)
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", prompt_system),
                ("user", prompt_user),
            ]
        )
        chain = prompt | model
    else:
        parser = PydanticOutputParser(pydantic_object=cls)
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    prompt_system
                    + "\n\n格式描述如下：\n{format_instructions}\n注意回答请用中文。",
                ),
                ("user", prompt_user),
            ]
        ).partial(format_instructions=parser.get_format_instructions())
        chain = prompt | model | parser
    return chain
