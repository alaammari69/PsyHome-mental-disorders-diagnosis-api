import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_deepseek import ChatDeepSeek
from langchain_groq import ChatGroq

load_dotenv(dotenv_path=Path(__file__).parent.parent / "core" / ".env")

class LLMModels:

    _groq_llm_model = None
    _deepseek_llm_model = None

    @classmethod
    def get_groq_llm_model(cls)-> ChatGroq:
        # checks if there's no current model applied to the static variable
        if cls._groq_llm_model is None:
             # create a new connection to the Groq api and save it in the static variable of the class
            cls._groq_llm_model = ChatGroq(
                model= os.getenv("GROQ_MODEL_NAME"),
                temperature = float(os.getenv("GROQ_TEMPERATURE")),
                api_key= os.getenv("GROQ_API_KEY"),
            )
        return cls._groq_llm_model

    @classmethod
    def get_deepseek_llm_model(cls)->ChatDeepSeek:

        # checks if there's no current model applied to the static variable
        if cls._deepseek_llm_model is None:
            # create a new connection to the DeepSeek api and save it in the static variable of the class
            cls._deepseek_llm_model = ChatDeepSeek(
                model= os.getenv("DEEPSEEK_MODEL_NAME"),
                temperature = float(os.getenv("DEEPSEEK_TEMPERATURE")),
                api_key= os.getenv("DEEPSEEK_API_KEY"),
            )
        return cls._deepseek_llm_model

    def get_deepseek_llm_structured(schema):
        return LLMModels.get_deepseek_llm_model().with_structured_output(
            schema=schema, method="json_mode"
        )
