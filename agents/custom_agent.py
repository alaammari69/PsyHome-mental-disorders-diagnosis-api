from langchain.agents import create_agent

from ml_models.llms import LLMModels
from agents.custom_tools import *

class SymptomExtractionAgent:
    agent = None
    context = None
    memory = None


    def _create_agent(self, context: PatientContext):
        self.agent = create_agent(self.context)