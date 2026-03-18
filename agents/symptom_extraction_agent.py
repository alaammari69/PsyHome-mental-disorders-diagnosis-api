import psycopg
from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain_core.messages import SystemMessage, ToolMessage, AIMessage

from langgraph.checkpoint.postgres import PostgresSaver #this is what's gonna handle all the saving and reloading of the messages automatically

from langchain.messages import HumanMessage

from ml_models.llms import LLMModels
from agents.custom_tools import *
from models.context_classes import PatientContext
from models.response_schemas import SymptomExtractionAgentResponse, ExtractedSymptomSchema
from prompts.custom_templates import symptom_extraction_prompt

from repository.patient_symptoms_dao import PatientSymptomDAO

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

def _export_extracted_symptoms_to_DB(user_id:int, thread_id: str, symptoms: list[ExtractedSymptomSchema])->bool:
    """
    this method is used to save extracted symptoms to the DB
    :param user_id: user id
    :param thread_id: thread or session id
    :param symptoms: list of symptoms from the structured output of the agent
    :return:
    """
    try:
        if symptoms is None:
            print("No symptoms to save")
            return True

        for symptom in symptoms:
            PatientSymptomDAO.insert_or_update_max_intensity(
                patient_id=user_id,
                symptom_id=int(symptom.symptom_id),
                thread_id=thread_id,
                intensity=int(symptom.symptom_existence)
            )
        return True
    except Exception as e:
        print("saving symptoms failed")
        print(e)
        return False

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
            tools=[get_patient_info, get_relevant_symptoms_data, extract_related_undiagnosed_symptoms_and_disorders],# passing the tools that are only for extracting symptoms (still working on other tools...)
            context_schema=PatientContext, # the schema of the context (not the context itself, it's going to be passed in the invoke() method)
            response_format= ToolStrategy(SymptomExtractionAgentResponse),# the schema which the response should be in (the output is a structured response)
            checkpointer=self.checkpointer, # responsible for managing the memory automatically
            system_prompt=symptom_extraction_prompt # a prompt for the agent containing the instructions
        )

        # IMPORTANT FOR THE MEMORY (CHECKPOINTER)
        # this object is going to be passed in the invoke() method
        # this is what's going to specify to the checkpointer what messages to retrieve and where to save
        self.config = {
            "configurable" : {"thread_id": context.thread_id, "user_id" : context.user_id}
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
        structured_response = response["structured_response"]

        # saving the extracted symptoms according to the user and thread (session)
        _export_extracted_symptoms_to_DB(
            user_id=self.context.user_id,
            thread_id=self.context.thread_id,
            symptoms=structured_response.extracted_symptoms
        )

        return structured_response

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
        return self.send_system_message("SESSION_RESET")

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


@tool
@tool
def extract_related_undiagnosed_symptoms_and_disorders(runtime: ToolRuntime[PatientContext], symptoms: list[dict]):
    """
    Retrieves all symptoms and their parent disorders that belong to the same disorder cluster(s)
    as the given symptoms, excluding any symptoms the patient has already been assessed for
    (whether confirmed or marked as non-existent). Use this to discover new, unassessed clinically
    related symptoms and understand their disorder context, enabling smarter and more targeted
    follow-up questions.

    WHEN TO CALL THIS:
    - After extracting one or more symptoms from the user's message
    - When you want to ask a follow-up question grounded in clinical context
    - When you suspect the user may have related symptoms they haven't described yet

    AGENT INSTRUCTIONS:
    1. Use 'related_disorders' to understand the clinical context of the symptom cluster
    2. Use 'related_symptoms' to identify unassessed symptoms the user has NOT yet mentioned
    3. Cross-reference both to pick the most clinically relevant follow-up question
    4. NEVER ask about all returned symptoms at once — ask about ONE at a time
    5. Do NOT reveal symptom or disorder names directly to the user — translate them into
       natural, conversational language.
       Example: instead of "Do you experience anhedonia?" ask "Have you found it hard
       to enjoy things you used to like?"
    6. If 'related_symptoms' is empty, all related symptoms have already been assessed —
       broaden your questioning or move to a different disorder cluster.

    :param runtime: The tool runtime context containing the authenticated patient session,
                    used to fetch the patient's symptom history for filtering
    :param symptom_ids: List of already extracted symptom IDs to use as reference points
    :return: A dictionary with two keys:
             - 'related_disorders': list of disorder records associated with the symptom cluster,
               each containing disorder_id and disorder_name
             - 'related_symptoms': deduplicated list of unassessed symptom records, each
               containing symptom_id, symptom_name, symptom_description, and disorder_id.
               Empty if all related symptoms have already been assessed.
    """

    print("get_related_symptoms_and_disorders tool is used !")

    # get the needed context variables
    patient_id = runtime.context.user_id
    all_related_symptoms = []

    for symptom in symptoms:

        # first we retrieve the disorder_id from the symptom
        disorder_id = int(symptom["disorder_id"])

        # then we get all the related symptoms to that disorder
        related_symptoms = SymptomDAO.get_by_disorder(disorder_id=disorder_id)
        all_related_symptoms.append(related_symptoms)

    if not all_related_symptoms:
        return []

     # combine all symptoms dataframes into one DataFrame
    combined_symptoms = pd.concat(all_related_symptoms, ignore_index=True)
    combined_symptoms.drop_duplicates(subset="symptom_id", inplace=True)

    # remove unwanted data
    combined_symptoms.drop(columns=["created_at", "updated_at"], inplace=True)

    # we remove all the already diagnosed symptoms or the ones that are specified as non-existent (intensity = -1)
    patient_symptom_history = PatientSymptomDAO.get_by_patient_id(patient_id=patient_id)
    ids_to_drop = patient_symptom_history["symptom_id"].tolist()
    print(ids_to_drop)
    combined_symptoms.drop(combined_symptoms[combined_symptoms["symptom_id"].isin(ids_to_drop)].index, inplace=True)

    # get all the related disorders (to allow the agent for a better decision-making to pick the next question)
    disorder_ids = (combined_symptoms["disorder_id"].unique().tolist())
    related_disorders = DisorderDAO.get(disorder_id=disorder_ids)
    related_disorders.drop(columns=["created_at", "updated_at"], inplace=True)


    result_dict = {
        "related_disorders": related_disorders.to_dict(orient="records"),
        "related_symptoms": combined_symptoms.to_dict(orient="records"),
    }
    print("***********************************************************")
    print(result_dict)
    print("***********************************************************")
    return result_dict


