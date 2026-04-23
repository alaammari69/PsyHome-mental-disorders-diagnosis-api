import datetime
from wsgiref.headers import Headers

import pandas as pd
from fastapi import FastAPI, Header, HTTPException
import re
from fastapi.middleware.cors import CORSMiddleware
import os
import json

from jose import jwt
from pandas import DataFrame

from repository.patient_dao import PatientDAO
from repository.patient_symptoms_dao import PatientSymptomDAO
from repository.patientthreaddao import PatientThreadDAO
from repository.psychiatristsdao import PsychiatristDAO
from services.rest_requests_classes import PsyLoginRequest, PsySignUpRequest

from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "core" ,".env"))

# fast api app that handles middlewares, routes etc...
app = FastAPI()

# adding all the allowed middlewares to connect to the api
app.add_middleware(
    middleware_class=CORSMiddleware,
    allow_origins=[os.getenv("FRONT_END_ALLOWED_DOMAIN")],
    allow_methods=["*"],
    allow_headers=["*"],
)

#***************************************************************************************************************
#***************************************************************************************************************
#..........................................LOGIN / SIGNUP.......................................................
#***************************************************************************************************************
#***************************************************************************************************************
@app.post("/psychiatrist_login")
def psychiatrist_login(request: PsyLoginRequest):
    psychiatrist = PsychiatristDAO.get_by_email_password(request.email.strip(), request.password.strip())
    print(psychiatrist)
    if not psychiatrist.empty:

        # processs.........
        return {
            "token": generate_token(psychiatrist= psychiatrist)
        }
    else:
        return {}

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
# password should have at least 8 characters: 1 lower case, 1 uppercase, 1 degit and one special character
PASSWORD_REGEX = re.compile(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,}$')

# cin should be 8 digits
CIN_PHONE_REGEX = re.compile(r'^\d{8}$')

def generate_token(psychiatrist: DataFrame)->str:
    psychiatrist.drop(columns=["created_at", "updated_at"], inplace = True) # unnecessary columns
    psychiatrist["date_of_birth"] = psychiatrist["date_of_birth"].astype(str)
    print(psychiatrist["date_of_birth"])
    payload = psychiatrist.to_dict(orient="records")[0]
    token = jwt.encode(
        claims = payload,
        key = os.getenv('JWT_SECRET_KEY'),
        algorithm = os.getenv('JWT_ALGORITHM')
    )
    return token

def verify_token(authorization: str = Header()):
    try:
        payload = jwt.decode(
            token=authorization,
            key=os.getenv('JWT_SECRET_KEY'),
            algorithms=os.getenv('JWT_ALGORITHM')
        )
        return payload
    except:
        raise HTTPException(status_code=401, detail="Could not validate token")

def validate_email(email: str) -> bool:
    return bool(EMAIL_REGEX.match(email))

def validate_password(password: str) -> bool:
    return bool(PASSWORD_REGEX.match(password))
def validate_cin_phone(cin: str)->bool:
    return bool(CIN_PHONE_REGEX.match(cin))


#***************************************************************************************************************
#***************************************************************************************************************
#................................................PATIENTS.......................................................
#***************************************************************************************************************
#***************************************************************************************************************

@app.get("/all_patients")
def all_patients():
    patients = PatientDAO.get_all()

    # change the format to calculate the age
    patients["date_of_birth"] = pd.to_datetime(patients["date_of_birth"])
    patients["age"] = (datetime.datetime.now() - patients["date_of_birth"]).dt.days // 365

    patients["fullname"] = patients["first_name"] + " " + patients["last_name"]
    patients["sessions"] = patients["patient_id"].apply(PatientThreadDAO.nbr_threads_per_patient)
    patients["lastSession"] = patients["patient_id"].apply(PatientThreadDAO.last_session_date)
    patients["active_sessions"] = patients["patient_id"].apply(PatientThreadDAO.nbr_active_threads_per_patient)

    patients.drop(columns=["created_at","first_name","last_name","date_of_birth","external_ref"], inplace = True)
    patients_dict = patients.to_dict(orient="records")
    #print(patients_dict)
    return patients_dict

