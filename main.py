import os

from langchain_core.messages import HumanMessage, AIMessage

from agents.diagnosis_agent import DiagnosisAgent
from agents.symptom_extraction_agent import SymptomExtractionAgent
from models.context_classes import PatientContext

from dotenv import load_dotenv
from rich import print
from embedder.embedders import HuggingFaceEmbedder
from repository.diagnosisdao import DiagnosisDAO
from repository.patient_dao import PatientDAO
from repository.patient_symptoms_dao import PatientSymptomDAO

from devtools import debug

load_dotenv()

HuggingFaceEmbedder.get_embedder()

# Press the green button in the gutter to run the script.
if __name__ == '__main__':

    exit_code = os.getenv("EXIT_CODE_END_OF_CONVERSATION")

    context = PatientContext(
        user_id=2,
        thread_id="50",
    )

    symptom_extraction_agent = SymptomExtractionAgent(
        context=context,
    )

    messages = symptom_extraction_agent.get_previous_conversation()
    print(type(messages))
    if messages is not None:
        for msg in messages:
            if type(msg) is HumanMessage:
                print(f"You: {msg.content}\n")
            if type(msg) is AIMessage:
                print(f"AI Assistant: {msg.content}\n")

    result = symptom_extraction_agent.reset_session()
    print(result.response)


    while True:

        user_message = input("You: ")
        if user_message == "exit":
            break
        result = symptom_extraction_agent.send_human_message(user_message)
        #print(result)
        print(f"AI Assistant: {result.response}")

        if exit_code in result.response:
            messages = symptom_extraction_agent.get_previous_conversation()
            # *******************************
            print("00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000")
            diagnosis_agent = DiagnosisAgent()
            diagnosis_agent.load_patient_info(PatientDAO.get(patient_id=context.patient_id).to_dict(orient="records"))
            diagnosis_agent.load_chat_history(messages=messages)
            diagnosis_agent.load_patient_symptoms(PatientSymptomDAO.get_by_patient_id(patient_id=context.patient_id).to_dict(orient="records"))

            diagnosis = diagnosis_agent.generate_diagnosis()
            print(diagnosis)
            print("00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000")
            # *******************************

            break
