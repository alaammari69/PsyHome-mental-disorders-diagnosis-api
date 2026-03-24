import os

import pandas as pd
import numpy as np
from langchain_core.tools import tool
from langgraph.prebuilt import ToolRuntime

from embedder.embedders import HuggingFaceEmbedder
from models.context_classes import PatientContext, Symptom, Disorder
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
    print_debug("///////////////////////////\nget_patient_info tool is used !\n//////////////////////////")

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
    this tool is used to save the current user's prompt
    it take the RAW UNMODIFIED user prompt and save it to the runtime context
    :param runtime: runtime
    :param user_prompt: user prompt
    :return: None
    """
    print_debug("////////////////////////\nsave_user_text tool is used !\n/////////////////////////")

    runtime.context.user_text = user_prompt

@tool
def get_expected_symptoms(runtime: ToolRuntime[PatientContext])->Symptom|None:
    """
    this tool is used to get the expected symptoms from the context
    :param runtime: runtime
    :return: dictionary containing a single expected symptom
    """
    print_debug("////////////////////////\nget_expected_symptoms tool is used !\n/////////////////////////")

    expected_symptom = runtime.context.expected_symptom
    return expected_symptom

@tool
def is_expected_symptom_confirmed(runtime: ToolRuntime[PatientContext], confirmation: bool)->None:
    """
    this tool is used to confirm the existence or not of a symptom in question
    then automatically saves the result
    :param runtime: runtime
    :param confirmation: True if yes, False if no or no expected symptom exists
    :return: None
    """
    print_debug("////////////////////////\nis_expected_symptom_confirmed tool is used !\n/////////////////////////")

    # get the expected symptom from the context
    expected_symptom = runtime.context.expected_symptom

    if expected_symptom is not None:
        # either fully confirmed or denied
        if confirmation:
            intensity = 0
        else:
            intensity = 10

        # get the other necessary values
        patient_id = runtime.context.patient_id
        thread_id = runtime.context.thread_id
        symptom_id = expected_symptom.symptom_id

        print_debug(f"symptom in question {symptom_id} : intensity {intensity}")

        # save in the DataBase
        PatientSymptomDAO.insert_or_update_max_intensity(
            patient_id=patient_id,
            thread_id=thread_id,
            symptom_id=symptom_id,
            intensity=intensity
        )
        runtime.context.expected_symptom = None

@tool
def get_relevant_symptoms_data(runtime: ToolRuntime[PatientContext]) -> dict:
    """
    this method returns the POSSIBLE extant symptoms in the patient
    the results are not confined, but more like candidates with the highest probability of existence
    in the current flow of the conversation
    """
    print_debug("////////////////////////\nget_relevant_symptoms_data tool is used !\n/////////////////////////")

    user_prompt = runtime.context.user_text # first we retrieve the user prompt

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
    ))

    # retuned the data found
    if len(relevant_data) == 0:
        return {"message": "No closely matching symptoms found"}
    else :
        return relevant_data.head(max_symptoms).to_dict(orient="records")


@tool(args_schema=SaveExtractedSymptomsArgs)
def save_extracted_symptoms(runtime: ToolRuntime[PatientContext],extracted_symptoms: list[ExtractedSymptomSchema]) -> None:
    """
    this tool takes the extracted symptoms from the agent, and saves all the symptoms in the context list
    and in the DataBase
    :param runtime: runtime
    :param extracted_symptoms: extracted symptoms
    :return:
    """
    print_debug("//////////////////////\nsave_extracted_symptoms tool is used !\n//////////////////////")

    runtime.context.new_extracted_symptoms.clear()
    runtime.context.new_extracted_symptoms.extend(extracted_symptoms)

    patient_id = runtime.context.patient_id
    thread_id = runtime.context.thread_id

    print_debug(f"extracted_symptoms: {extracted_symptoms}")

    if extracted_symptoms:
        for symptom in extracted_symptoms:
            PatientSymptomDAO.insert_or_update_max_intensity(
                patient_id=patient_id,
                thread_id=thread_id,
                symptom_id=symptom.symptom_id,
                intensity=symptom.intensity
            )



@tool
def extract_related_undiagnosed_symptoms_and_disorders(runtime: ToolRuntime[PatientContext])->None:
    """
    this tool takes the extracted symptoms from the agent, and then saves all the related symptoms in the context list
    :param runtime:
    :return:
    """

    print_debug("//////////////////////\nget_related_symptoms_and_disorders tool is used !\n//////////////////////")

    # get the needed context variables
    patient_id = runtime.context.patient_id

    # get all the patient's symptoms history
    all_extracted_symptoms_df = PatientSymptomDAO.get_by_patient_id(patient_id=patient_id)
    all_related_symptoms = []

    for symptom in all_extracted_symptoms_df.iterrows():

        # we only extract related symptoms of confirmed existing ones
        if symptom["intensity"] != 0:

            # first we retrieve the disorder_id from the symptom
            disorder_id = int(symptom["disorder_id"])

            # then we get all the related symptoms to that disorder
            related_symptoms = SymptomDAO.get_by_disorder(disorder_id=disorder_id)
            all_related_symptoms.append(related_symptoms)


    # combine all symptoms dataframes into one DataFrame
    combined_symptoms = pd.concat(all_related_symptoms, ignore_index=True)
    combined_symptoms.drop_duplicates(subset="symptom_id", inplace=True)  # since there would be a lot of duplicates

    # remove unwanted data
    combined_symptoms.drop(columns=["created_at", "updated_at", "embedding"], inplace=True)

    # we remove all the already diagnosed symptoms or the ones that are specified as non-existent (intensity = 0)
    patient_symptom_history = PatientSymptomDAO.get_by_patient_id(patient_id=patient_id)  # this gets all the patient's symptoms history
    ids_to_drop = patient_symptom_history["symptom_id"].tolist()
    print_debug("ids to drop: "+ids_to_drop)
    combined_symptoms.drop(combined_symptoms[combined_symptoms["symptom_id"].isin(ids_to_drop)].index, inplace=True)

    # get all the related disorders (to allow the agent for a better decision-making to pick the next question)
    disorder_ids = (combined_symptoms["disorder_id"].unique().tolist())
    related_disorders = DisorderDAO.get(disorder_id=disorder_ids)
    related_disorders.drop(columns=["created_at", "updated_at"], inplace=True)

    # at the end we save each list in the context for the other tools
    # IMPORTANT: the save happens only if the current values in the context are not empty lists
    if (runtime.context.possible_related_disorders != []) and (runtime.context.possible_related_symptoms != []):

        # we use this trigger to follow if we actually updated the lists with new values or not
        runtime.context.stage_of_diagnosis = True
        # save related disorders in the context variable
        runtime.context.possible_related_disorders.clear()  # clear the old list
        related_disorders.apply(lambda related_disorder: runtime.context.possible_related_disorders.append(
            Disorder(
                disorder_id=int(related_disorder["disorder_id"]),
                disorder_name=related_disorder["disorder_name"],
                dsm_code=related_disorder["dsm_code"],
                category_id=int(related_disorder["category_id"]),
                is_subtype=related_disorder["is_subtype"],
                parent_disorder_id=int(related_disorder["parent_disorder_id"])
            )
        ))
        # save related symptoms in the context variable
        runtime.context.possible_related_symptoms.clear()  # clear the old list
        combined_symptoms.apply(lambda related_symptom: runtime.context.possible_related_symptoms.append(
            Symptom(
                symptom_id=int(related_symptom["symptom_id"]),
                disorder_id=int(related_symptom["disorder_id"]),
                symptom_name=related_symptom["symptom_name"],
                symptom_description=related_symptom["symptom_description"]
            )
        ))
    else: # this means that there are no related symptoms left to as for (they all either confirmed or discarded)

        # we flip the trigger to


    #conver to list[dict] instead of DataFrame
    related_disorders_dict = related_disorders.to_dict(orient="records")
    related_symptoms_dict = combined_symptoms.to_dict(orient="records")

    # for debugging !!!
    result_dict = {
        "related_disorders": related_disorders_dict,
        "related_symptoms": related_symptoms_dict,
    }
    print_debug("***********************************************************")
    print_debug(result_dict)
    print_debug("***********************************************************")


@tool
def get_related_symptoms_and_disorders(runtime: ToolRuntime[PatientContext]):
    """
    this tool is used to get the related symptoms and disorders, and it's the agent role to pick a single symptom from this (if not null ofc)
    :param runtime:
    :return:
    """

    print_debug("//////////////////////\nget_related_symptoms_and_disorders tool is used !\n//////////////////////")
    related_disorders = runtime.context.possible_related_disorders
    related_symptoms = runtime.context.possible_related_symptoms

    related_dict = {
        "related_disorders": related_disorders,
        "related_symptoms": related_symptoms
    }
    print_debug(related_dict)
    return related_dict

@tool
def commit_expected_symptom(runtime: ToolRuntime[PatientContext], expected_symptom_id: int)->Symptom:
    """
    this commits what symptom is most like gonna be present in the context variable
    :param runtime:
    :param symptom_id:
    :return:
    """
    if expected_symptom_id != -1:
        expected_symptom = SymptomDAO.get(symptom_id=expected_symptom_id)

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