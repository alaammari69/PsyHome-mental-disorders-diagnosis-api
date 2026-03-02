import psycopg
from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy

from langgraph.checkpoint.postgres import PostgresSaver #this is what's gonna handle all the saving and reloading of the messages automatically

from langchain.messages import HumanMessage

from ml_models.llms import LLMModels
from agents.custom_tools import *
from models.context_classes import PatientContext
from models.response_schemas import SymptomExtractionAgentResponse
from prompts.custom_templates import symptom_extraction_prompt

from rich import print

from repository.dbconnector import DBConnector


def _create_checkpointer()-> PostgresSaver:
    """
    this function's only role is to create the checkpointer
    by creating a postgres connection using the connection_string
    of the database from DBconnector.
    :return: checkpointer
    """
    postgres_conn = DBConnector().get_psycopg_connection()

    checkpointer = PostgresSaver(postgres_conn)
    checkpointer.setup()
    return checkpointer


class SymptomExtractionAgent:

    def __init__(self, context: PatientContext):
        # the context has the necessary values for the constructor (user_id and sessio_id)
        # to create an agent with the right parameters
        self.context = context

        # this checkpointer is the object that's managing the messages of the user and the AI by :
        # 1. automatically create the tables to store the info of the messages
        # 2. saving automatically the messages to the database (the info of the db are passed to the PostgresSaver constructor) using the user_id and thread_id as keys
        # 3. retrieving automatically the messages if they exist suing the user_id and thread_id (each 1 user has 0-n threads)
        self.checkpointer = _create_checkpointer()
        self.agent = create_agent(
            model=LLMModels.get_deepseek_llm_model(), # using deepseek as the main model (BaseModel)
            tools=[get_patient_info, get_relevant_symptoms_data],# passing the tools that are only for extracting symptoms (still working on other tools...)
            context_schema=PatientContext, # the schema of the context (not the context itself, it's going to be passed in the invoke() method)
            response_format= ToolStrategy(SymptomExtractionAgentResponse),# the schema which the response should be in (the output is a structured response)
            checkpointer=self.checkpointer, # responsible for managing the memory automatically
            system_prompt=symptom_extraction_prompt # a prompt for the agent containing the instructions
        )

        # IMPORTANT FOR THE MEMORY (CHECKPOINTER)
        # this object is going to be passed in the invoke() method
        # this is what's going to specify to the checkpointer what messages to retrieve and where to save
        self.config = {
            "configurable" : {"thread_id": context.session_id, "user_id" : context.user_id}
        }



    def send_message(self, user_prompt: str)->SymptomExtractionAgentResponse:
        response = self.agent.invoke(
            input={"messages" : [HumanMessage(content=user_prompt)]},
            context=self.context,
            config=self.config
        )
        print(response)
        return response["structured_response"]

    def get_all_messages(self):
        """
        this method is to get all messages from a certain user_id and thread_id passed in the constructor
        :return: history messages
        """
        checkpointer_tuple = self.checkpointer.get_tuple(config= self.config)

        return checkpointer_tuple[1]['channel_values']['messages']
