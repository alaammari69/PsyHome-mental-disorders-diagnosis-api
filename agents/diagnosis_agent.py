from langchain.agents import create_agent
from langchain_core.messages import SystemMessage, HumanMessage

from agents.custom_tools import get_related_disorders_and_symptoms, get_patient_info
from ml_models.llms import LLMModels
from models.context_classes import PatientContext
from models.response_schemas import DiagnosisAgentResponse
from prompts.system_prompts import diagnosis_prompt

class DiagnosisAgent:
    def __init__(self):
        # creating a langchain agent specifically for the diagnosis stage
        self.agent = create_agent(
            model=LLMModels.get_deepseek_llm_model(),
            tools = [get_related_disorders_and_symptoms],
            response_format=DiagnosisAgentResponse,
            system_prompt=diagnosis_prompt
        )
        self.chat_history=None
        self.patient_info=None
        self.patient_symptoms=None

    # this method is to load the chat history into the agent system prompt
    def load_chat_history(self,messages: list)->None:
        self.chat_history = ""
        if self.chat_history is not None:
            for msg in messages:
                role = "Patient" if msg.__class__.__name__ == "HumanMessage" else "Assistant"
                self.chat_history += f"{role}: {msg.content}\n"

    def load_patient_info(self, patient_info: dict)->None:
        self.patient_info = patient_info

    def load_patient_symptoms(self, patient_symptoms: dict)->None:
        self.patient_symptoms = patient_symptoms

    def generate_diagnosis(self)->DiagnosisAgentResponse|None:
        if self.chat_history is None:
            print("No chat history provided")
            return None
        if self.patient_info is None:
            print("No patient info provided")
            return None
        if self.patient_symptoms is None:
            print("No patient symptoms provided")

        print("Patient Info:")
        print(self.patient_info)
        print("Patient Symptoms:")
        print(self.patient_symptoms)
        print("chat history:")
        print(self.chat_history)
        response = self.agent.invoke({
            "messages": [
                HumanMessage(content=f"""
        Chat History:
        {self.chat_history}

        Patient Info:
        {self.patient_info}

        Patient Symptoms:
        {self.patient_symptoms}

        Instruction:
        GENERATE_DIAGNOSIS
        """)
            ]
        })
        return response["structured_response"]

