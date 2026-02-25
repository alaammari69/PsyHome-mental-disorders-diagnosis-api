from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy

from langchain.messages import HumanMessage, SystemMessage
from ml_models.llms import LLMModels
from agents.custom_tools import *
from models.context_classes import PatientContext
from prompts.custom_templates import symptom_extraction_prompt
from models.response_schemas import SymptomExtractionAgentResponse

from rich import print

class SymptomExtractionAgent:
    agent = None
    context = None
    memory = None
    conversation = None

    def __init__(self, context: PatientContext):
        self.conversation = {
            "messages": [
                            SystemMessage(symptom_extraction_prompt),
                            SystemMessage("start with greeting the patient")
                         ]
        }

        self.context = context
        self.memory = None # still figuring out memory
        self.agent = create_agent(
            model=LLMModels.get_deepseek_llm_model(),
            tools=[get_patient_info, get_relevant_symptoms_data],
            context_schema=PatientContext,
            response_format= ToolStrategy(SymptomExtractionAgentResponse)
            #checkpointer=memory
        )


    def send_message(self, user_prompt: str = None)->SymptomExtractionAgentResponse:

        if user_prompt is not None:
            self.conversation["messages"].append(HumanMessage(content=user_prompt))


        response = self.agent.invoke({
                "messages" : self.conversation["messages"]
            },
            context=self.context
        )

        self.conversation["messages"] = response["messages"]

        print(len(response["messages"]))
        print(response["messages"])

        return response["structured_response"]

