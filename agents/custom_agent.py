from langchain.agents import create_agent

from langchain.messages import HumanMessage

from agents.custom_agents import conversation, response
from ml_models.llms import LLMModels
from agents.custom_tools import *
from models.context_classes import PatientContext
from prompts.custom_templates import symptom_extraction_prompt_template

class SymptomExtractionAgent:
    _agent = None
    _context = None
    _memory = None

    _conversation = {
        "messages": []
    }


    def __init__(self, context: PatientContext):
        self.context = context
        self.memory = None # still figuring out memory
        self.agent = create_agent(
            model=LLMModels.get_deepseek_llm_model(),
            tools=[get_patient_info, get_relevant_symptoms_data],
            context_schema=PatientContext
            #checkpointer=memory
        )


    def send_message(self, user_prompt: str = None):

        if user_prompt is not None:
            conversation["messages"].append(HumanMessage())

        prompt = symptom_extraction_prompt_template.format(conversation)

        response = self.agent.invoke(
            conversation
        )

        return response

