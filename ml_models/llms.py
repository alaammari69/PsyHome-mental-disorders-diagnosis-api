import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_deepseek import ChatDeepSeek
from langchain_groq import ChatGroq


class LLMModels:

    _groq_llm_model = None
    _deepseek_llm_model = None

    @classmethod
    def get_groq_llm_model(cls):
        if cls._groq_llm_model is None:
            env_path = Path(__file__).parent.parent / "core" / ".env"

            if not env_path.exists():
                raise FileNotFoundError(f".env not found at {env_path}")

            load_dotenv(dotenv_path=env_path)

            cls._groq_llm_model = ChatGroq(
                model= os.getenv("GROQ_MODEL_NAME"),
                temperature = float(os.getenv("GROQ_TEMPERATURE")),
                api_key= os.getenv("GROQ_API_KEY"),
            )
        return cls._groq_llm_model

    @classmethod
    def get_deepseek_llm_model(cls):
        if cls._deepseek_llm_model is None:
            env_path = Path(__file__).parent.parent / "core" / ".env"

            if not env_path.exists():
                raise FileNotFoundError(f".env not found at {env_path}")

            load_dotenv(dotenv_path=env_path)

            cls._deepseek_llm_model = ChatDeepSeek(
                model= os.getenv("DEEPSEEK_MODEL_NAME"),
                temperature = float(os.getenv("DEEPSEEK_TEMPERATURE")),
                api_key= os.getenv("DEEPSEEK_API_KEY"),
            )
        return cls._deepseek_llm_model
