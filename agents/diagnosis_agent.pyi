from langchain.agents import create_agent

from ml_models.llms import LLMModels


class DiagnosisAgent:
    def __init__(self):
        self.agent = create_agent(
            model=LLMModels.get_deepseek_llm_model(),
            tools = [],
            response_format=,
            system_prompt=
        )