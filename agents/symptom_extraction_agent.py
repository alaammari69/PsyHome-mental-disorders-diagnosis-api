from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain_core.messages import SystemMessage, AIMessage

from langgraph.checkpoint.postgres import PostgresSaver #this is what's gonna handle all the saving and reloading of the messages automatically

from langchain.messages import HumanMessage

from agents.custom_tools import get_patient_info, get_relevant_symptoms_data, \
    extract_related_undiagnosed_symptoms_and_disorders, save_user_text, get_expected_symptom, \
    is_expected_symptom_confirmed, save_extracted_symptoms, is_diagnosis_stage, get_related_symptoms_and_disorders, \
    commit_expected_symptom
from ml_models.llms import LLMModels
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
            tools=[
                get_patient_info,
                save_user_text,
                get_expected_symptom,
                is_expected_symptom_confirmed,
                get_relevant_symptoms_data,
                save_extracted_symptoms,
                extract_related_undiagnosed_symptoms_and_disorders,
                is_diagnosis_stage,
                get_related_symptoms_and_disorders,
                commit_expected_symptom
            ],# passing the tools that are only for extracting symptoms (still working on other tools...)
            context_schema=PatientContext, # the schema of the context (not the context itself, it's going to be passed in the invoke() method)
            response_format= ToolStrategy(SymptomExtractionAgentResponse),# the schema which the response should be in (the output is a structured response)
            checkpointer=self.checkpointer, # responsible for managing the memory automatically
            system_prompt=symptom_extraction_prompt # a prompt for the agent containing the instructions
        )

        # IMPORTANT FOR THE MEMORY (CHECKPOINTER)
        # this object is going to be passed in the invoke() method
        # this is what's going to specify to the checkpointer what messages to retrieve and where to save
        self.config = {
            "configurable" : {"thread_id": context.thread_id, "user_id" : context.patient_id}
        }

        # these variable are used mainly for generating a question that's relevant to the patient
        self.possible_undiagnosed_symptoms = []
        self.possible_undiagnosed_disorders = []
        self.current_questioned_symptom = None



    def send_human_message(self, user_prompt: str)->SymptomExtractionAgentResponse:

        # first step is generating the response
        response = self.agent.invoke(
            input={"messages" : [HumanMessage(content=user_prompt)]},
            context=self.context,
            config=self.config
        )
        # extracting the structured format of the response
        #print(response)
        return response["structured_response"]

    def send_system_message(self, developer_prompt: str)->SymptomExtractionAgentResponse:
        response = self.agent.invoke(
            input={"messages": [SystemMessage(content=developer_prompt)]},
            context=self.context,
            config=self.config
        )
        #print(response)
        return response["structured_response"]

    def reset_session(self)->SymptomExtractionAgentResponse:
        """
        this method is used to notify the agent that conversation was interrupted for a period of time
        so the agent would update its context automatically
        and greet the user again
        :return: a response to the user
        """
        return self.send_system_message("__SESSION_INIT__")

    def get_all_messages(self):
        """
        this method is to get all messages from a certain user_id and thread_id passed in the constructor
        in the format of SystemMessages and ToolMessages
        :return: history messages
        """
        checkpointer_tuple = self.checkpointer.get_tuple(config= self.config)
        if checkpointer_tuple is not None:
            return checkpointer_tuple[1]['channel_values']['messages']
        else:
            return None


    def get_previous_conversation(self):
        conversation = []
        messages = self.get_all_messages()

        if messages is None:
            return None
        #print(messages)
        for msg in messages:
            if type(msg) is not SystemMessage: # filtering out all the SystemMessages

                # if it's a HumanMessage then we add it directly
                if type(msg) is HumanMessage:
                    conversation.append(HumanMessage(content=msg.content))

                # if it's an AIMessage that means it is directed to the agent
                # since the response is a structured output, we nned to get the structured data right from the args of the SymptomExtractionAgentResponse tool call
                # and then extract only the 'response' argument
                # otherwise if we get it from a ToolMessage, it would be one long text with everything unstructured
                elif type(msg) is AIMessage:

                    if msg.tool_calls: # if the list of tool calls is not empty then we check what tools are called and look for one needed
                        for tool_call in msg.tool_calls:
                            if tool_call['name'] == "SymptomExtractionAgentResponse":  # this is the type of tools we are looking for

                                # append it as a new AIMessage BUT the content itself now is in the 'content' attribute for easy access
                                conversation.append(AIMessage(
                                    content=tool_call["args"]["response"]
                                ))

        return conversation

