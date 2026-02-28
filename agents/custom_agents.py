import psycopg
from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy

from langgraph.checkpoint.postgres import PostgresSaver

from langchain.messages import HumanMessage

from ml_models.llms import LLMModels
from agents.custom_tools import *
from models.context_classes import PatientContext
from models.response_schemas import SymptomExtractionAgentResponse
from prompts.custom_templates import symptom_extraction_prompt

from rich import print

from repository.dbconnector import DBConnector


class SymptomExtractionAgent:

    def __init__(self, context: PatientContext):
        self.context = context

        self.checkpointer = self._create_checkpointer() # still figuring out memory
        self.agent = create_agent(
            model=LLMModels.get_deepseek_llm_model(),
            tools=[get_patient_info, get_relevant_symptoms_data],
            context_schema=PatientContext,
            response_format= ToolStrategy(SymptomExtractionAgentResponse),
            checkpointer=self.checkpointer
        )

        self.config = {
            "configurable" : {"thread_id": context.session_id, "user_id" : context.user_id}
        }



    def send_message(self, user_prompt: str)->SymptomExtractionAgentResponse:
        response = self.agent.invoke(
            input={"messages" : [HumanMessage(content=user_prompt)]},
            context=self.context,
            config=self.config
        )
        return response["structured_response"]

    def _create_checkpointer(self):
        conn_string = DBConnector().get_connection_string()
        postgres_conn = psycopg.connect(
            conninfo=conn_string,
            autocommit=True
        )

        checkpointer = PostgresSaver(postgres_conn)
        checkpointer.setup()
        return checkpointer


