import os
from typing import Any

import pandas as pd
import numpy as np
from langchain_core.tools import tool
from langgraph.prebuilt import ToolRuntime
from pandas import DataFrame

from embedder.embedders import HuggingFaceEmbedder
from models.context_classes import PatientContext
from repository.patient_dao import PatientDAO
from repository.patient_disorders_dao import PatientDisorderDAO
from repository.patient_symptoms_dao import PatientSymptomDAO
from repository.symptomdao import SymptomDAO
from repository.disorderdao import DisorderDAO


from rich import print



@tool
def get_relevant_symptoms_data(runtime: ToolRuntime[PatientContext],user_prompt: str) -> dict:
    """
    Analyzes the user's message against the clinical database to identify up to 6 candidate symptoms (Threshold: 0.18).

    IMPORTANT:
    - ONLY call this when the user describes experiences, emotions, or relationship patterns.
    - NEVER call this for greetings, small talk, or your own generated text.
    - Provide the EXACT, unmodified user message.

    AGENT INSTRUCTIONS FOR MULTI-SYMPTOM EXTRACTION:
    1. SCORING HIERARCHY: Symptoms with higher dot_product scores are stronger leads. Prioritize these for extraction.
    2. MULTI-EXTRACTION: Extract ALL symptoms that apply — both explicitly stated and implied by the user's words.
       Do not settle for just one symptom if the user's message suggests multiple.
    3. INFERRED EXTRACTION: Users rarely use clinical language. Match the emotional and behavioral meaning
       behind their words to the returned symptoms, not just literal keyword matches.
       Examples:
       - "I feel worthless" → extract low self-esteem, self-criticism, negative self-image if returned
       - "I can't stop thinking about it" → extract intrusive thoughts, rumination if returned
       - "Nothing makes me happy anymore" → extract anhedonia, emotional numbness if returned
    4. CLINICAL VALIDATION: Use the 'symptom_name' to cross-reference the user's phrasing.
       If a candidate is mathematically similar but clinically irrelevant to the context, omit it.
    5. CONFIDENCE THRESHOLD: If a symptom is returned with a score > 0.25 and matches the user's
       sentiment (directly or implied), extract it decisively — do not second-guess.
    6. BIAS TOWARD EXTRACTION: When uncertain, lean toward extracting a symptom rather than omitting it.
       It is safer to flag a potential symptom for review than to miss it entirely.

    :param user_prompt: The exact HumanMessage content.
    :return: A dictionary containing the top semantically similar symptoms and their clinical scores.
    """
    print("////////////////////////\nget_relevant_symptoms_data tool is used !\n/////////////////////////")


    runtime.context.last_user_text = user_prompt # first we save the user prompt for future use cases

    # we get the embedder instance and then embedd the user_prompt
    embedder = HuggingFaceEmbedder.get_embedder()
    embedded_prompt = embedder.embed_query(user_prompt)

    # using the embedded user_prompt, we calculate the dot product for each symptom with the user_prompt
    data = SymptomDAO.get_all()
    data["dot_product"] = data["embedding"].apply(lambda x: np.dot(x, embedded_prompt))

    # we sort the values by the dot_product (higher value means more semantic similarity)
    data.sort_values(by="dot_product", ascending=False, inplace=True)

    print(data[["symptom_name", "dot_product"]].sort_values(by="dot_product", ascending=False)) # for debugging purposes ...


    threshold = float(os.environ["SYMPTOM_EXTRACTION_THRESHOLD"])
    max_symptoms = int(os.environ["SYMPTOM_EXTRACTION_MAX_SYMPTOMS"])

    # filter out the noise from the data (dot product is very low so it could return false data)
    relevant_data = data[data["dot_product"] > threshold]

    # remove the embeddings column since it's not used after this step,
    # and we remove any other columns that are not useful in the process
    relevant_data.drop(columns=["embedding", "created_at", "updated_at"], inplace=True)

    # retuned the data found
    if len(relevant_data) == 0:
        return {"message": "No closely matching symptoms found"}
    else :
        return relevant_data.head(max_symptoms).to_dict(orient="records")


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
    print("///////////////////////////\nget_patient_info tool is used !\n//////////////////////////")

    # get patient_id from the context to retrieve the patient's personal information
    patient_id = runtime.context.user_id
    patient_info = PatientDAO.get(patient_id)

    # checks if the patient is registered in the database by seeing if the patient_info is not a None value
    if patient_info is not None:

        # we get the patient disorder and symptoms history by the patient_id
        patient_symptom_history=PatientSymptomDAO.get_by_patient_id(patient_id=patient_id)
        patient_disorder_history= PatientDisorderDAO.get_by_patient_id(patient_id=patient_id)

        # combined all the retrieved data into one dictionary to return it
        full_information_dict = {
            "patient_personal_information": patient_info.to_dict(orient="records"),
            "patient_symptoms_history": patient_symptom_history.drop(columns="patient_id").to_dict(orient="records"),
            "patient_disorders_history": patient_disorder_history.drop(columns="patient_id").to_dict(orient="records"),
        }

        print(full_information_dict)

        return full_information_dict
    else:
        return {"message": "Patient not found in database"}


@tool
def extract_related_undiagnosed_symptoms_and_disorders(runtime: ToolRuntime[PatientContext], symptoms: list[dict]):
    """
    this tool takes the extracted symptoms from the agent, and then saves all the related symptoms in the context list
    :param runtime:
    :param symptoms:
    :return:
    """

    print("//////////////////////\nget_related_symptoms_and_disorders tool is used !\n//////////////////////")

    # get the needed context variables
    patient_id = runtime.context.user_id
    all_related_symptoms = []

    for symptom in symptoms:
        # first we retrieve the disorder_id from the symptom
        disorder_id = int(symptom["disorder_id"])

        # then we get all the related symptoms to that disorder
        related_symptoms = SymptomDAO.get_by_disorder(disorder_id=disorder_id)
        all_related_symptoms.append(related_symptoms)

    if not all_related_symptoms:  # end the tool if there are no related symptoms
        return

    # combine all symptoms dataframes into one DataFrame
    combined_symptoms = pd.concat(all_related_symptoms, ignore_index=True)
    combined_symptoms.drop_duplicates(subset="symptom_id", inplace=True)  # since there would be a lot of duplicates

    # remove unwanted data
    combined_symptoms.drop(columns=["created_at", "updated_at"], inplace=True)

    # we remove all the already diagnosed symptoms or the ones that are specified as non-existent (intensity = -1)
    patient_symptom_history = PatientSymptomDAO.get_by_patient_id(patient_id=patient_id)  # this gets all the patient's symptoms history
    ids_to_drop = patient_symptom_history["symptom_id"].tolist()
    print(ids_to_drop)
    combined_symptoms.drop(combined_symptoms[combined_symptoms["symptom_id"].isin(ids_to_drop)].index, inplace=True)

    # get all the related disorders (to allow the agent for a better decision-making to pick the next question)
    disorder_ids = (combined_symptoms["disorder_id"].unique().tolist())
    related_disorders = DisorderDAO.get(disorder_id=disorder_ids)
    related_disorders.drop(columns=["created_at", "updated_at"], inplace=True)

    #conver to list[dict] instead of DataFrame
    related_disorders_dict = related_disorders.to_dict(orient="records")
    related_symptoms_dict = combined_symptoms.to_dict(orient="records")

    # for debugging !!!
    result_dict = {
        "related_disorders": related_disorders_dict,
        "related_symptoms": related_symptoms_dict,
    }
    print("***********************************************************")
    print(result_dict)
    print("***********************************************************")

    # at the end we save each list in the context for the other tools
    # IMPORTANT: the save happens only if the current values in the context are empty lists
    if (runtime.context.possible_related_symptoms != []) and (runtime.context.possible_related_disorders != []):
        runtime.context.possible_related_symptoms = related_symptoms_dict
        runtime.context.possible_related_disorders = related_disorders_dict

    return

@tool
def get_related_symptoms_and_disorders(runtime: ToolRuntime[PatientContext]):
    """
    this tool is used to get the related symptoms and disorders, and it's the agent role to pick a single symptom from this (if not null ofc)
    :param runtime:
    :return:
    """

    print("get_related_symptoms_and_disorders tool is used !")
    related_disorders = runtime.context.possible_related_disorders
    related_symptoms = runtime.context.possible_related_symptoms

    return {
        "related_disorders": related_disorders,
        related_symptoms: related_symptoms
    }

@tool
def commit_expected_symptom(runtime: ToolRuntime[PatientContext], symptom_id: int):
    """
    commit
    :param runtime:
    :param symptom_id:
    :return:
    """
    runtime.context.commited_symptom_id_for_making_sure= SymptomDAO.get(symptom_id=symptom_id).to_dict(orient="dict")
@tool
def get_expected_symptom(runtime: ToolRuntime[PatientContext]):
    """
    gets the exact symptom that's gonna be put on the test
    :param runtime:
    :return:
    """
    symptom_id = runtime.context.commited_symptom_id_for_making_sure
    return SymptomDAO.get(symptom_id=symptom_id).to_dict()

@tool
def is_the_commited_symptoms_exists(runtime: ToolRuntime[PatientContext], exists: bool):
    return False
