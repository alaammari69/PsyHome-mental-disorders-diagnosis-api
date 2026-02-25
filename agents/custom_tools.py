import os

import numpy as np
from langchain_core.tools import tool
from langgraph.prebuilt import ToolRuntime

from ml_models.embedders import HuggingFaceEmbedder
from models.context_classes import PatientContext
from repository.patient_dao import PatientDAO
from repository.patient_symptoms_dao import PatientSymptomDAO
from repository.symptomdao import SymptomDAO



symptoms_data_schema = {
    "type": "object",
    "properties": {
        "user_prompt": {"type": "string"}
    },
    "required": ["user_prompt"]
}

@tool(args_schema=symptoms_data_schema)
def get_relevant_symptoms_data(user_prompt: str) -> dict:
    """
    This function is used to get the relevant data from the user_prompt to extract possible symptoms.

    IMPORTANT:
    - ONLY call this tool when the user has sent a message describing their symptoms or experience
    - NEVER call this tool with your own generated text or greeting — only with the exact user message
    - If there is no user message yet, do NOT call this tool
    - :param user_prompt: The user prompt (HumanMessage content) exactly as it is (no modifications to it)
    - :return: dict with relevant data that could help with the symptom extraction
    """
    embedder = HuggingFaceEmbedder.get_embedder()
    embedded_prompt = embedder.embed_query(user_prompt)

    data = SymptomDAO.get_all()


    data["dot_product"] = data["embedding"].apply(lambda x: np.dot(x, embedded_prompt))

    data.sort_values(by="dot_product", ascending=False, inplace=True)

    print(data[["symptom_name", "dot_product"]].sort_values(by="dot_product", ascending=False)) # for debugging purposes ...

    threashhold = float(os.environ["SYMPTOM_EXTRACTION_THREASHHOLD"])


    relevant_data = data[data["dot_product"] > threashhold]
    relevant_data.drop(columns=["embedding"], inplace=True)

    if len(relevant_data) == 0:
        return {"message": "No closely matching symptoms found"}
    else :
        return relevant_data.head(5).to_dict(orient="records")


@tool
def get_patient_info(runtime: ToolRuntime[PatientContext]) -> dict:
    """
    this function is used to get the patient info from the context values

    This tool should be called when patient-specific details are needed to
    personalize responses or make informed clinical decisions. It automatically
    resolves the patient identity from the active session context

    The returned patient profile may include demographic details, medical history,
    and any previously diagnosed mental health conditions

    Returns a dictionary containing the patient's profile data if found,
    or a descriptive error message if the patient does not exist in the database

    :param runtime: The tool runtime context containing the authenticated
                    patient session, including the patient_id used for lookup
    :return: A dict with the patient's information (e.g. name, age, medical
             history, diagnosed mental disorders), or {"message": "Patient not
             found in database"} if no matching record exists
    """
    print("TOOL IS USED !")
    patient_id = runtime.context.patient_id

    patient = PatientDAO.get(patient_id)
    if patient is not None:
        return patient.to_dict()
    else:
        return {"message": "Patient not found in database"}



extracted_symptoms_schema = {
    "type": "object",
    "properties": {
        "symptom_id": {"type": "int"}
    },
    "required": ["user_prompt"]
}
@tool
def export_extracted_symptoms(runtime: ToolRuntime[PatientContext],
                              symptom_id: int,
                              intensity: int
                              ) -> None:
    """
        Export extracted symptoms to the database for the current patient.
        If the symptom already exists, update it only if the new intensity is higher.
        If the symptom doesn't exist, insert it.

        :param runtime: Runtime context containing patient_id
        :param symptom_id: The ID of the symptom to export
        :param intensity: The intensity level of the symptom (typically 1-10)
        :return: None
    """

    patient_id = runtime.context.patient_id
    test = PatientSymptomDAO.check_symptom_exists(patient_id, symptom_id)

    if test:
        previous_intensity = PatientSymptomDAO.get_by_patient_symptom_id(patient_id,symptom_id)["intensity"][0]
        if intensity > previous_intensity:
            PatientSymptomDAO.update(
                patient_id=patient_id,
                symptom_id=symptom_id,
                intensity=intensity,
            )
    else:
        PatientSymptomDAO.insert(
            patient_id=patient_id,
            symptom_id=symptom_id,
            intensity=intensity,
        )