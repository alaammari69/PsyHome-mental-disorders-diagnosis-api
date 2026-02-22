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
    this function is used to get the relevant data to user_prompt to extract possible symptoms
    :param user_prompt: The user prompt
    :return: dict with relevant data
    """
    embedder = HuggingFaceEmbedder.get_embedder()
    embedded_prompt = embedder.embed_query(user_prompt)

    data = SymptomDAO.get_all()


    data["dot_product"] = data["embedding"].apply(lambda x: np.dot(x, embedded_prompt))

    data.sort_values(by="dot_product", ascending=False, inplace=True)

    print(data[["symptom_name", "dot_product"]].sort_values(by="dot_product", ascending=False))

    relevant_data = data[data["dot_product"] > 0.29]
    relevant_data.drop(columns=["embedding"], inplace=True)

    if len(relevant_data) == 0:
        return {"message": "No closely matching symptoms found"}
    else :
        return relevant_data.head(5).to_dict(orient="records")


@tool
def get_patient_info(runtime: ToolRuntime[PatientContext]) -> dict:
    """
    this function is used to get the patient info from the context values
    :param runtime:
    :return: dict with patient info
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