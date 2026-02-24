from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy

from langchain.messages import HumanMessage, SystemMessage
from ml_models.llms import LLMModels
from agents.custom_tools import *
from models.context_classes import PatientContext
from prompts.custom_templates import symptom_extraction_prompt_template
from models.response_schemas import symptom_extraction_schema

class SymptomExtractionAgent:
    agent = None
    context = None
    memory = None
    conversation = None

    def __init__(self, context: PatientContext):
        self.conversation = {
            "messages": []
        }
        self.context = context
        self.memory = None # still figuring out memory
        self.agent = create_agent(
            model=LLMModels.get_deepseek_llm_model(),
            tools=[get_patient_info, get_relevant_symptoms_data],
            context_schema=PatientContext,
            response_format= ToolStrategy(symptom_extraction_schema)
            #checkpointer=memory
        )


    def send_message(self, user_prompt: str = None):

        if user_prompt is not None:
            self.conversation["messages"].append(HumanMessage(content=user_prompt))

        prompt = symptom_extraction_prompt_template.format(conversation=self.conversation)

        response = self.agent.invoke({
            "messages": [SystemMessage(prompt)],
            "context": self.context
        })

        conversation = response

        return response["structured_response"]

