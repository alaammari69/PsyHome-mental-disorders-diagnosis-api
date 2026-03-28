import os

import pandas as pd
import numpy as np
from langchain_core.tools import tool
from langgraph.prebuilt import ToolRuntime

from embedder.embedders import HuggingFaceEmbedder
from models.context_classes import PatientContext, Symptom, Disorder, StageOfDiagnosis
from models.custom_enums import SymptomLikelihood
from models.tool_arguments_schemas import SaveExtractedSymptomsArgs, ExtractedSymptomSchema
from repository.patient_dao import PatientDAO
from repository.patient_disorders_dao import PatientDisorderDAO
from repository.patient_symptoms_dao import PatientSymptomDAO
from repository.symptomdao import SymptomDAO
from repository.disorderdao import DisorderDAO


from rich import print

debugMode = True


# this method is only used to turn off and on all the console messages easily
def print_debug(obj)->None:
    if debugMode:
        print(obj)

#********************************************************************************************************************
#********************************************SYMPTOM_EXTRACTION_AGENT TOOLS******************************************
#********************************************************************************************************************

@tool
def get_patient_info(runtime: ToolRuntime[PatientContext]) -> dict:
    """
    Retrieves the full patient profile from the database.

    Includes personal information, previously diagnosed disorders,
    and symptom history associated with the patient.

    :return: dict with keys patient_personal_information, patient_symptoms_history,
             patient_disorders_history, or {"message": "Patient not found in database"}
             if no record exists.
    """
    print_debug("///////////////////////////\nget_patient_info tool is used !\n")

    # get patient_id from the context to retrieve the patient's personal information
    patient_id = runtime.context.patient_id
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

        print_debug(full_information_dict)

        return full_information_dict
    else:
        print_debug({"message": "Patient not found in database"})
        return {"message": "Patient not found in database"}


@tool
def save_user_text(runtime: ToolRuntime[PatientContext], user_prompt: str)->None:
    """
    Saves the raw unmodified user message to the session context.

    :param user_prompt: The exact message sent by the user, no modifications.
    :return: None
    """
    print_debug("////////////////////////\nsave_user_text tool is used !")

    runtime.context.user_text = user_prompt

    print_debug(f"user_text : {runtime.context.user_text} -> SAVED")

@tool
def get_expected_symptom(runtime: ToolRuntime[PatientContext])-> Symptom | None:
    """
    Returns the currently pending symptom from the session context.

    The pending symptom is one that was selected in a previous turn
    and is awaiting confirmation from the patient.

    :return: The pending Symptom object, or None if no symptom is currently pending.
    """
    print_debug("////////////////////////\nget_expected_symptoms tool is used !\n")

    expected_symptom = runtime.context.expected_symptom

    print_debug(f"symptom in question : {expected_symptom}")

    return expected_symptom

@tool
def is_expected_symptom_confirmed(runtime: ToolRuntime[PatientContext], confirmation: str)->None:
    """
    Records the agent's confidence assessment of the pending symptom based on
    the patient's response, then saves the result and clears the pending symptom.

    Has no effect if no symptom is currently pending.

    :param confirmation: Confidence level as a string. Must be one of:
                         ABSENT    - patient explicitly denied it
                         UNLIKELY  - patient contradicts or pushes back
                         NEUTRAL   - unclear, ambiguous, or patient unsure
                         LIKELY    - implied by tone, context, or partially confirmed
                         CONFIRMED - explicitly and clearly stated by patient
    :return: None
    """
    print_debug("////////////////////////\nis_expected_symptom_confirmed tool is used !\n")

    # get the expected symptom from the context
    expected_symptom = runtime.context.expected_symptom

    if expected_symptom is not None:

        # get the other necessary values
        patient_id = runtime.context.patient_id
        thread_id = runtime.context.thread_id
        symptom_id = expected_symptom.symptom_id
        confidence = SymptomLikelihood[confirmation].value

        print_debug(f"symptom in question {symptom_id} : confidence {confidence}")

        # save in the DataBase
        PatientSymptomDAO.insert_or_update_max_confidence(
            patient_id=patient_id,
            thread_id=thread_id,
            symptom_id=symptom_id,
            confidence=confidence
        )
        runtime.context.expected_symptom = None
    else:
        print_debug("no symptom to confirm")

@tool
def get_relevant_symptoms_data(runtime: ToolRuntime[PatientContext]) -> dict:
    """
    Returns symptom candidates that are semantically related to the current user message.

    Computes dot product similarity between the embedded user message and all symptoms
    in the database. Only symptoms scoring above 0.18 are considered, higher scores
    indicate stronger semantic relevance and a higher likelihood of existence in the patient,
    but these are candidates only — not confirmed symptoms.

    It is the agent's responsibility to assess which candidates are actually
    present based on the context of the conversation.

    :return: List of candidate symptom records as dicts ordered by relevance score,
             or {"message": "No closely matching symptoms found"} if no symptom
             passes the 0.18 threshold.
    """
    print_debug("////////////////////////\nget_relevant_symptoms_data tool is used !\n")

    user_prompt = runtime.context.user_text # first we retrieve the user prompt

    print_debug(f"user prompt: {user_prompt}")

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

    # save the relevant symptoms in the context for future use :
    runtime.context.relevant_symptoms_data.clear()
    relevant_data.apply(lambda x: runtime.context.relevant_symptoms_data.append(
        Symptom(
            symptom_id=x["symptom_id"],
            symptom_name=x["symptom_name"],
            symptom_description=x["symptom_description"],
            disorder_id=x["disorder_id"]
        )
    ),axis=1)

    # retuned the data found
    if len(relevant_data) == 0:
        return {"message": "No closely matching symptoms found"}
    else :
        return relevant_data.head(max_symptoms).to_dict(orient="records")


@tool(args_schema=SaveExtractedSymptomsArgs)
def save_extracted_symptoms(runtime: ToolRuntime[PatientContext],extracted_symptoms: list[ExtractedSymptomSchema]) -> None:
    """
    Saves the agent's confidence assessment for all evaluated symptoms to
    the session context and database.

    Every symptom returned by get_relevant_symptoms_data should be included
    here with an appropriate confidence level — not just the ones that seem
    present. ABSENT and UNLIKELY grades are as valuable as CONFIRMED ones.

    :param extracted_symptoms: All evaluated symptoms with their confidence grades.
    :return: None
    """
    print_debug("//////////////////////\nsave_extracted_symptoms tool is used !\n")

    runtime.context.new_extracted_symptoms.clear()
    runtime.context.new_extracted_symptoms.extend(extracted_symptoms)

    patient_id = runtime.context.patient_id
    thread_id = runtime.context.thread_id

    print_debug(f"extracted_symptoms: {extracted_symptoms}")

    if extracted_symptoms:
        for symptom in extracted_symptoms:
            PatientSymptomDAO.insert_or_update_max_confidence(
                patient_id=patient_id,
                thread_id=thread_id,
                symptom_id=symptom.symptom_id,
                confidence=SymptomLikelihood[symptom.symptom_confidence].value
            )



@tool
def extract_related_undiagnosed_symptoms_and_disorders(runtime: ToolRuntime[PatientContext])->None:
    """
    Computes symptoms and disorders related to the patient's confirmed symptoms
    that have not yet been addressed.

    Fetches all symptoms related to confirmed ones, removes already extracted
    or denied ones, then saves the remaining candidates to context.

    :return: None
    """

    print_debug("//////////////////////\nget_related_symptoms_and_disorders tool is used !\n")

    # get the needed context variables
    patient_id = runtime.context.patient_id

    # get all the patient's symptoms history
    all_extracted_symptoms_df = PatientSymptomDAO.get_by_patient_id(patient_id=patient_id)
    all_related_symptoms = []

    for _, symptom in all_extracted_symptoms_df.iterrows():

        # we extract related symptoms of likely existing ones
        if SymptomLikelihood[symptom["confidence"]] >= SymptomLikelihood.LIKELY:

            # first we retrieve the disorder_id from the symptom
            symptom_id = int(symptom["symptom_id"])
            disorder_id = int(SymptomDAO.get(symptom_id=symptom_id).iloc[0]["disorder_id"])

            # then we get all the related symptoms to that disorder
            related_symptoms = SymptomDAO.get_by_disorder(disorder_id=disorder_id)
            all_related_symptoms.append(related_symptoms)


    # combine all symptoms dataframes into one DataFrame

    # in case no related symptoms found (the only time this would be true is at the beginning
    # when the patient is still never had a symptom extracted
    if not all_related_symptoms:
        runtime.context.stage_of_diagnosis = StageOfDiagnosis.DIAGNOSIS
        return

    combined_symptoms = pd.concat(all_related_symptoms, ignore_index=True)
    combined_symptoms.drop_duplicates(subset="symptom_id", inplace=True)  # since there would be a lot of duplicates

    # remove unwanted data
    combined_symptoms.drop(columns=["created_at", "updated_at", "embedding"], inplace=True)

    # we remove all the already diagnosed symptoms
    patient_symptom_history = PatientSymptomDAO.get_by_patient_id(patient_id=patient_id)  # this gets all the patient's symptoms history
    ids_to_drop = patient_symptom_history["symptom_id"].tolist()
    print_debug(f"ids to drop: {ids_to_drop}")
    combined_symptoms.drop(combined_symptoms[combined_symptoms["symptom_id"].isin(ids_to_drop)].index, inplace=True)



    # at the end we save each list in the context for the other tools
    # IMPORTANT: the save happens only if the current possible_related_symptoms value in the context is NOT empty list
    if not combined_symptoms.empty:

        # we use this trigger to follow if we actually updated the lists with new values or not
        runtime.context.stage_of_diagnosis = StageOfDiagnosis.SYMPTOM_EXTRACTION

        # get all the related disorders (to allow the agent for a better decision-making to pick the next question)
        disorder_ids = (combined_symptoms["disorder_id"].unique().tolist())
        related_disorders = DisorderDAO.get(disorder_id=disorder_ids)
        related_disorders.drop(columns=["created_at", "updated_at"], inplace=True)

        # save related disorders in the context variable
        runtime.context.possible_related_disorders.clear()  # clear the old list

        related_disorders.apply(lambda related_disorder: runtime.context.possible_related_disorders.append(
                Disorder(
                    disorder_id=int(related_disorder["disorder_id"]),
                    disorder_name=related_disorder["disorder_name"],
                    dsm_code=related_disorder["dsm_code"],
                    category_id=int(related_disorder["category_id"]),
                    is_subtype=related_disorder["is_subtype"],
                    parent_disorder_id=None if pd.isna(related_disorder["parent_disorder_id"]) else int(related_disorder["parent_disorder_id"])
                )
            ),
            axis=1
        )
        # save related symptoms in the context variable
        runtime.context.possible_related_symptoms.clear()  # clear the old list
        combined_symptoms.apply(lambda related_symptom: runtime.context.possible_related_symptoms.append(
            Symptom(
                symptom_id=int(related_symptom["symptom_id"]),
                disorder_id=int(related_symptom["disorder_id"]),
                symptom_name=related_symptom["symptom_name"],
                symptom_description=related_symptom["symptom_description"]
            )
        ),axis=1)
    else: # this means that there are no related symptoms left to ask for (they all either confirmed or discarded)

        # we change the state so we can signal that we should move to the diagnosis step
        if runtime.context.stage_of_diagnosis == StageOfDiagnosis.SYMPTOM_EXTRACTION:
            runtime.context.stage_of_diagnosis = StageOfDiagnosis.DIAGNOSIS
        return

    #conver to list[dict] instead of DataFrame
    related_disorders_dict = related_disorders.to_dict(orient="records")
    related_symptoms_dict = combined_symptoms.to_dict(orient="records")

    # for debugging !!!
    result_dict = {
        "related_disorders": related_disorders_dict,
        "related_symptoms": related_symptoms_dict,
    }
    print_debug(result_dict)


@tool
def is_diagnosis_stage(runtime: ToolRuntime[PatientContext])->str:
    """
    Returns the current stage of the diagnostic session. (future implementation)

    :return: "DIAGNOSIS_STAGE_REACHED" if all symptoms have been addressed,
             "CONTINUE" if symptom extraction is still in progress.
    """
    print_debug("////////////////////////\nis_diagnosis_stage tool is used !\n")
    print_debug("CONTINUE")
    return "CONTINUE"

@tool
def get_related_symptoms_and_disorders(runtime: ToolRuntime[PatientContext]):
    """
    Returns the unaddressed related symptoms and disorders from context.

    :return: dict with keys related_symptoms (list of Symptom) and
             related_disorders (list of Disorder).
    """

    print_debug("//////////////////////\nget_related_symptoms_and_disorders tool is used !\n")
    related_disorders = runtime.context.possible_related_disorders
    related_symptoms = runtime.context.possible_related_symptoms

    related_dict = {
        "related_disorders": related_disorders,
        "related_symptoms": related_symptoms
    }
    print_debug(f"number of possible related symptoms: {len(related_symptoms)}")
    return related_dict

@tool
def commit_expected_symptom(runtime: ToolRuntime[PatientContext], expected_symptom_id: int)->Symptom|None:
    """
    Sets a symptom as the pending symptom to be confirmed next turn.

    Saves the selected symptom to context and removes it from the
    related symptoms list to avoid re-selecting it.

    :param expected_symptom_id: ID of the symptom to commit. Pass -1 to skip (no symptom to commit).
    :return: The committed Symptom object, or None if -1 was passed.
    """
    print_debug("//////////////////////\ncommit_expected_symptom tool is used !\n")

    if expected_symptom_id != -1:
        expected_symptom = SymptomDAO.get(symptom_id=expected_symptom_id).iloc[0]

        runtime.context.expected_symptom = Symptom(
            symptom_id=int(expected_symptom["symptom_id"]),
            disorder_id=int(expected_symptom["disorder_id"]),
            symptom_name=expected_symptom["symptom_name"],
            symptom_description=expected_symptom["symptom_description"]
        )

        # filter out this symptom from the related symptoms
        runtime.context.possible_related_symptoms = [
            s for s in runtime.context.possible_related_symptoms
            if s.symptom_id != expected_symptom_id
        ]

        print_debug(runtime.context.expected_symptom)

        return runtime.context.expected_symptom
    else:
        return None


#********************************************************************************************************************
#********************************************SYMPTOM_EXTRACTION_AGENT TOOLS******************************************
#********************************************************************************************************************