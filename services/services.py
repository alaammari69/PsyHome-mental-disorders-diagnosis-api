import datetime
from wsgiref.headers import Headers
from langchain.messages import HumanMessage, AIMessage

import pandas as pd
from fastapi import FastAPI, Header, HTTPException
import re
from fastapi.middleware.cors import CORSMiddleware
import os
import json
import re

from jose import jwt
from pandas import DataFrame
from sympy import true

from agents.symptom_extraction_agent import SymptomExtractionAgent
from models.context_classes import PatientContext
from repository.diagnosisdao import DiagnosisDAO
from repository.patient_dao import PatientDAO
from repository.patient_disorders_dao import PatientDisorderDAO
from repository.patient_symptoms_dao import PatientSymptomDAO
from repository.patientthreaddao import PatientThreadDAO
from repository.psychiatristsdao import PsychiatristDAO
from repository.symptomdao import SymptomDAO
from services.rest_requests_classes import PsyLoginRequest, PsySignUpRequest, PatientCreateRequest, \
    PatientUpdateRequest, PatientDeleteRequest

from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "core", ".env"))

# fast api app that handles middlewares, routes etc...
app = FastAPI()

# adding all the allowed middlewares to connect to the api
app.add_middleware(
    middleware_class=CORSMiddleware,
    allow_origins=[os.getenv("FRONT_END_ALLOWED_DOMAIN")],
    allow_methods=["*"],
    allow_headers=["*"],
)

is_debug_mode = os.getenv("REST_SERVICES_DEBUGGING")
def debug_print(obj: object) -> None:
    if is_debug_mode:
        print(obj)


#***************************************************************************************************************
#***************************************************************************************************************
#..........................................LOGIN / SIGNUP.......................................................
#***************************************************************************************************************
#***************************************************************************************************************

@app.post("/psychiatrist_login")
def psychiatrist_login(request: PsyLoginRequest):
    psychiatrist = PsychiatristDAO.get_by_email_password(request.email.strip(), request.password.strip())
    debug_print(psychiatrist)
    if not psychiatrist.empty:
        # process.........
        return {"token": generate_token(psychiatrist=psychiatrist)}
    else:
        return {"token": ""}

@app.post("/psychiatrist_signup")
def psychiatrist_signup(request: PsySignUpRequest):
    response = {
        "success": True,
        "email_error": False,
        "password_error": False,
        "cin_error": False,
        "phone_error": False,
    }
    if not validate_email(request.email):
        response["success"] = False
        response["email_error"] = True
    if not validate_password(request.password):
        response["success"] = False
        response["password_error"] = True
    if not validate_cin_phone(request.cin):
        response["success"] = False
        response["cin_error"] = True
    if not validate_cin_phone(request.phone):
        response["success"] = False
        response["phone_error"] = True

    if response["success"] is False:
        return response
    # signup process .......

    return response


# email should be valid before verification
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
# password should have at least 8 characters: 1 lower case, 1 uppercase, 1 digit and one special character
PASSWORD_REGEX = re.compile(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,}$')
# cin should be 8 digits
CIN_PHONE_REGEX = re.compile(r'^\d{8}$')

def generate_token(psychiatrist: DataFrame) -> str:
    psychiatrist.drop(columns=["created_at", "updated_at"], inplace=True)  # unnecessary columns
    psychiatrist["date_of_birth"] = psychiatrist["date_of_birth"].astype(str)  # change the formatting of the date for compatibility with JWT

    debug_print(psychiatrist["date_of_birth"])

    payload = psychiatrist.to_dict(orient="records")[0]
    token = jwt.encode(
        claims=payload,
        key=os.getenv('JWT_SECRET_KEY'),
        algorithm=os.getenv('JWT_ALGORITHM')
    )
    debug_print(token)
    return token

def verify_token(authorization: str = Header()):
    payload = jwt.decode(
        token=authorization,
        key=os.getenv('JWT_SECRET_KEY'),
        algorithms=os.getenv('JWT_ALGORITHM')
    )
    return payload

def validate_email(email: str) -> bool:
    return bool(EMAIL_REGEX.match(email))

def validate_password(password: str) -> bool:
    return bool(PASSWORD_REGEX.match(password))

def validate_cin_phone(cin: str) -> bool:
    return bool(CIN_PHONE_REGEX.match(cin))


#***************************************************************************************************************
#***************************************************************************************************************
#................................................PATIENTS.......................................................
#***************************************************************************************************************
#***************************************************************************************************************

@app.get("/patient/all")
def get_all_patients() -> list[dict] | dict:
    patients = PatientDAO.get_all()

    # change the format to calculate the age
    patients["date_of_birth"] = pd.to_datetime(patients["date_of_birth"])
    patients["age"] = (datetime.datetime.now() - patients["date_of_birth"]).dt.days // 365

    patients["fullname"] = patients["first_name"] + " " + patients["last_name"]
    patients["sessions"] = patients["patient_id"].apply(PatientThreadDAO.nbr_threads_per_patient)

    patients["lastSession"] = patients["patient_id"].apply(PatientThreadDAO.last_session_date)
    # to not cause any serialization problems when converting lastSession into json (if the result is NaN)
    patients["lastSession"] = pd.to_datetime(patients["lastSession"], errors="coerce")
    patients["lastSession"] = patients["lastSession"].dt.strftime("%Y-%m-%d %H:%M:%S")

    patients["active_sessions"] = patients["patient_id"].apply(PatientThreadDAO.nbr_active_threads_per_patient)

    patients.drop(columns=["created_at", "first_name", "last_name"], inplace=True)
    return patients.to_dict(orient="records")

@app.get("/patient/{patient_id}")
def get_patient(patient_id: int) -> dict:
    patient = PatientDAO.get(patient_id=patient_id)
    return patient.to_dict(orient="records")[0]

@app.get("/diagnosis/{diagnosis_id}")
def get_diagnosis(diagnosis_id: int):
    diagnosis = DiagnosisDAO.get(diagnosis_id=diagnosis_id)
    return diagnosis

@app.get("/patient/{patient_id}/threads")
def get_patient_threads(patient_id: int) -> list[dict] | dict:
    patient_threads = PatientThreadDAO.get_by_patient_id(patient_id=patient_id)
    return patient_threads.to_dict(orient="records")

@app.get("/patient/{patient_id}/symptoms")
def get_patient_symptoms(patient_id: int) -> list[dict] | dict:
    patient_symptoms = PatientSymptomDAO.get_patient_symptoms_full_description(patient_id=patient_id)
    patient_symptoms.drop(columns=["embedding", "created_at", "updated_at"], inplace=True)
    return patient_symptoms.to_dict(orient="records")

@app.get("/patient/{patient_id}/disorders")
def get_patient_disorders(patient_id: int) -> list[dict] | dict:
    patient_disorders = PatientDisorderDAO.get_by_patient_id_full_description(patient_id=patient_id)
    patient_disorders.drop(columns=["created_at", "updated_at"], inplace=True)
    return patient_disorders.to_dict(orient="records")

@app.post("/patient")
def create_patient(patient: PatientCreateRequest) -> dict:
    if validate_patient_info(patient):
        PatientDAO.insert(
            first_name=patient.first_name,
            last_name=patient.last_name,
            cin=patient.cin,
            gender=patient.gender,
            date_of_birth=patient.date_of_birth,
            username=patient.username,
            password=patient.password
        )
    return {}

@app.patch("/patient")
def update_patient(patient: PatientUpdateRequest) -> dict:
    if validate_patient_info(patient) and patient.patient_id:
        PatientDAO.update(
            patient_id=patient.patient_id,
            first_name=patient.first_name,
            last_name=patient.last_name,
            cin=patient.cin,
            gender=patient.gender,
            date_of_birth=patient.date_of_birth,
            username=patient.username,
            password=patient.password
        )
    return {}

@app.delete("/patient")
def delete_patient(patient: PatientDeleteRequest) -> dict:
    if patient.patient_id:
        PatientDAO.delete(patient_id=patient.patient_id)
    return {}


def validate_patient_info(patient_info: PatientCreateRequest) -> bool:
    # all fields are required; password must meet complexity rules; cin must be 8 digits
    if (
        not patient_info.first_name or
        not patient_info.last_name or
        not patient_info.username or
        not validate_password(patient_info.password) or
        not validate_cin_phone(patient_info.cin) or
        not patient_info.gender or
        not patient_info.date_of_birth
    ):
        return False
    return True


#***************************************************************************************************************
#***************************************************************************************************************
#................................................SESSIONS.......................................................
#***************************************************************************************************************
#***************************************************************************************************************

@app.get("/thread/{thread_id}/messages")
def get_patient_session(thread_id: int) -> list[AIMessage | HumanMessage] | dict:
    thread = PatientThreadDAO.get(thread_id=thread_id)
    threads_dict = thread.to_dict(orient="records")[0]

    patient_id = threads_dict["patient_id"]

    patient_context = PatientContext(user_id=patient_id, thread_id=str(thread_id))
    conversation_history = SymptomExtractionAgent.get_previous_conversation_readonly(patient_context)

    # strip the exit code marker from the last message so the frontend never sees it
    exit_code = os.getenv("EXIT_CODE_END_OF_CONVERSATION")
    for message in conversation_history:
        if exit_code in message.content:
            message.content = message.content.replace(exit_code, "").strip()

    return conversation_history

@app.get("/thread/{thread_id}")
def get_thread(thread_id: int) -> dict:
    thread = PatientThreadDAO.get(thread_id=thread_id)
    return thread.to_dict(orient="records")[0]