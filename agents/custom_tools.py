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
def get_relevant_symptoms_data(user_prompt: str) -> dict:
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
    embedder = HuggingFaceEmbedder.get_embedder()
    embedded_prompt = embedder.embed_query(user_prompt)

    data = SymptomDAO.get_all()


    data["dot_product"] = data["embedding"].apply(lambda x: np.dot(x, embedded_prompt))

    data.sort_values(by="dot_product", ascending=False, inplace=True)

    print(data[["symptom_name", "dot_product"]].sort_values(by="dot_product", ascending=False)) # for debugging purposes ...

    threshold = float(os.environ["SYMPTOM_EXTRACTION_THRESHOLD"])
    max_symptoms = int(os.environ["SYMPTOM_EXTRACTION_MAX_SYMPTOMS"])


    relevant_data = data[data["dot_product"] > threshold]
    relevant_data.drop(columns=["embedding"], inplace=True)

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
    print("TOOL IS USED !")
    patient_id = runtime.context.user_id
    thread_id = str(runtime.context.thread_id)


    patient_info = PatientDAO.get(patient_id)
    if patient_info is not None:
        patient_symptom_history=PatientSymptomDAO.get_by_patient_id(patient_id=patient_id)
        patient_disorder_history= PatientDisorderDAO.get_by_patient_id(patient_id=patient_id)
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
def get_related_symptoms_and_disorders(runtime: ToolRuntime[PatientContext],symptom_ids: list[int]):
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

    for symptom_id in symptom_ids:

        # first we retrieve the disorder_id from the symptom
        symptom = SymptomDAO.get(symptom_id=symptom_id)
        disorder_id = int(symptom["disorder_id"][0])

        # then we get all the related symptoms to that disorder
        related_symptoms = SymptomDAO.get_by_disorder(disorder_id=disorder_id)
        all_related_symptoms.append(related_symptoms)

    if not all_related_symptoms:
        return []

     # combine all symptoms dataframes into one DataFrame
    combined_symptoms = pd.concat(all_related_symptoms, ignore_index=True)
    combined_symptoms.drop_duplicates(subset="symptom_id", inplace=True)

    # we remove all the already diagnosed symptoms or the ones that are specified as non-existent (intensity = -1)
    patient_symptom_history = PatientSymptomDAO.get_by_patient_id(patient_id=patient_id)
    ids_to_drop = patient_symptom_history["symptom_id"].tolist()
    print(ids_to_drop)
    combined_symptoms.drop(combined_symptoms[combined_symptoms["symptom_id"].isin(ids_to_drop)].index, inplace=True)

    # get all the related disorders (to allow the agent for a better decision-making to pick the next question)
    disorder_ids = (combined_symptoms["disorder_id"].unique().tolist())
    related_disorders = DisorderDAO.get(disorder_id=disorder_ids)


    result_dict = {
        "related_disorders": related_disorders.to_dict(orient="records"),
        "related_symptoms": combined_symptoms.to_dict(orient="records"),
    }
    print("**************************************************************************************************")
    print(result_dict)
    print("**************************************************************************************************")
    return result_dict