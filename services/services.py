import asyncio
import datetime
import pandas as pd
from fastapi import FastAPI, Header, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
import os
import re

from jose import jwt, JWTError
from pandas import DataFrame
from sympy import false

from agents.diagnosis_agent import DiagnosisAgent
from agents.symptom_extraction_agent import SymptomExtractionAgent
from embedder.embedders import HuggingFaceEmbedder
from models.context_classes import PatientContext
from models.custom_enums import SymptomLikelihood
from repository.diagnosisdao import DiagnosisDAO
from repository.disorderdao import DisorderDAO
from repository.patient_dao import PatientDAO
from repository.patient_disorders_dao import PatientDisorderDAO
from repository.patient_symptoms_dao import PatientSymptomDAO
from repository.patientthreaddao import PatientThreadDAO
from repository.psychiatristsdao import PsychiatristDAO
from services.rest_requests_classes import PsyLoginRequest, PsySignUpRequest, PatientCreateRequest, \
    PatientUpdateRequest, PatientDeleteRequest, PsychiatristUpdatePasswordRequest, ThreadDeleteRequest, \
    AddPatientSymptomsRequest, AddPatientDisorderRequest, AddSessionRequest, PsychiatristDeleteRequest, \
    UpdatePsychiatristVerificationStatusRequest, UpdatePsychiatristAccessLevelRequest, PatientLoginRequest, \
    PatientChatRequest

from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "core", ".env"))
HuggingFaceEmbedder.get_embedder() # load embeddder into memory

# fast api app that handles middlewares, routes etc...
app = FastAPI()

# adding all the allowed middlewares to connect to the api
app.add_middleware(
    middleware_class=CORSMiddleware,
    allow_origins=[os.getenv("FRONT_END_ALLOWED_DOMAIN")],
    allow_methods=["*"],
    allow_headers=["*"],
)

is_debug_mode = True
def debug_print(obj: object) -> None:
    if is_debug_mode:
        print(obj)


# email should be valid before verification
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
# password should have at least 8 characters: 1 lower case, 1 uppercase, 1 digit and one special character
PASSWORD_REGEX = re.compile(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,}$')
# cin should be 8 digits
CIN_PHONE_REGEX = re.compile(r'^\d{8}$')


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
        # process....

        psychiatrist_dict = psychiatrist.to_dict(orient="records")[0]

        if psychiatrist_dict["account_verified"] is False:
            raise HTTPException(status_code=433, detail="account still not verified by admin")
        response = {"token": generate_token(psychiatrist=psychiatrist)}
        if psychiatrist_dict["psy_type"]=="PSY":
            response["type"]="PSY"
        elif psychiatrist_dict["psy_type"] == "ADMIN":
            response["type"]="ADMIN"
        return response
    else:
        raise HTTPException(status_code=400, detail="Incorrect email or password.")

@app.post("/psychiatrist_signup")
def psychiatrist_signup(request: PsySignUpRequest)->None:
    if validate_psy(request):
        PsychiatristDAO.insert(
            first_name=request.first_name,
            last_name=request.last_name,
            cin=request.cin,
            email=request.email,
            password=request.password,
            date_of_birth=request.date_of_birth,
            phone=request.phone,
            address=request.address,
            specialization=request.specialization,
            psy_type="PSY"
        )
    else:
        raise HTTPException(status_code=420, detail="invalid information")


def validate_psy(psy: PsySignUpRequest)->bool:
    if (
        not psy.first_name or
        not psy.last_name or
        not psy.email or
        not psy.cin or
        not psy.password or
        not psy.date_of_birth or
        not psy.phone or
        not psy.address or
        not psy.specialization
    ):
        raise HTTPException(status_code=420, detail="Missing information")
    if not validate_email(psy.email):
        raise HTTPException(status_code=420, detail="Invalid email")
    if not validate_password(psy.password):
        raise HTTPException(status_code=420, detail="Invalid password")
    if not validate_cin_phone(psy.cin):
        raise HTTPException(status_code=420, detail="Invalid CIN number")
    if not validate_cin_phone(psy.phone):
        raise HTTPException(status_code=420, detail="Invalid phone number")
    return True



def generate_token(psychiatrist: DataFrame) -> str:
    psychiatrist["date_of_birth"] = psychiatrist["date_of_birth"].astype(str)  # change the formatting of the date for compatibility with JWT
    psychiatrist["created_at"] = psychiatrist["created_at"].astype(str)
    psychiatrist["updated_at"] = psychiatrist["updated_at"].astype(str)

    debug_print(psychiatrist["date_of_birth"])

    payload = psychiatrist.to_dict(orient="records")[0]

    payload["exp"] = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=8) # this token expires after 8 hours (automatically gets verified when decoding)

    if payload["psy_type"] == "ADMIN":
        key = os.getenv('JWT_SECRET_KEY_ADMIN')
    elif payload["psy_type"] == "PSY":
        key = os.getenv('JWT_SECRET_KEY_PSY')

    token = jwt.encode(
        claims=payload,
        key=key,
        algorithm=os.getenv('JWT_ALGORITHM')
    )
    debug_print(token)
    return token

def verify_psychiatrist_token(authorization: str = Header()):
    try:
        payload = jwt.decode(
            token=authorization,
            key=os.getenv('JWT_SECRET_KEY_PSY'),
            algorithms=os.getenv('JWT_ALGORITHM')
        )
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

def verify_admin_token(authorization: str = Header()):
    try:
        payload = jwt.decode(
            token=authorization,
            key=os.getenv('JWT_SECRET_KEY_ADMIN'),
            algorithms=os.getenv('JWT_ALGORITHM')
        )
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

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
def get_all_patients(payload: dict = Depends(verify_psychiatrist_token)) -> list[dict] | dict:
    try:
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
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

@app.get("/patient/{patient_id}")
def get_patient(patient_id: int, payload: dict = Depends(verify_psychiatrist_token)) -> dict:
    try:
        patient = PatientDAO.get(patient_id=patient_id)
        return patient.to_dict(orient="records")[0]
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

@app.get("/diagnosis/{diagnosis_id}")
def get_diagnosis(diagnosis_id: int,payload: dict = Depends(verify_psychiatrist_token)):
    try:
        diagnosis = DiagnosisDAO.get(diagnosis_id=diagnosis_id)
        return diagnosis
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

@app.get("/patient/{patient_id}/threads")
def get_patient_threads(patient_id: int,payload: dict = Depends(verify_psychiatrist_token)) -> list[dict] | dict:
    try:
        patient_threads = PatientThreadDAO.get_by_patient_id(patient_id=patient_id)
        return patient_threads.to_dict(orient="records")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

@app.get("/patient/{patient_id}/symptoms")
def get_patient_symptoms(patient_id: int,payload: dict = Depends(verify_psychiatrist_token)) :
    try:
        patient_symptoms = PatientSymptomDAO.get_patient_symptoms_full_description(patient_id=patient_id)
        patient_symptoms.drop(columns=["embedding", "created_at", "updated_at"], inplace=True)
        return patient_symptoms.to_dict(orient="records")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

@app.get("/patient/{patient_id}/disorders")
def get_patient_disorders(patient_id: int,payload: dict = Depends(verify_psychiatrist_token)) -> list[dict] | dict:
    try:
        patient_disorders = PatientDisorderDAO.get_by_patient_id_full_description(patient_id=patient_id)
        patient_disorders.drop(columns=["created_at", "updated_at"], inplace=True)
        return patient_disorders.to_dict(orient="records")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

@app.post("/patient")
def create_patient(patient: PatientCreateRequest,payload: dict = Depends(verify_psychiatrist_token)) -> None:
    try:
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
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

@app.patch("/patient")
def update_patient(patient: PatientUpdateRequest,payload: dict = Depends(verify_psychiatrist_token)) -> None:
    try:
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
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

@app.delete("/patient")
def delete_patient(patient: PatientDeleteRequest,payload: dict = Depends(verify_psychiatrist_token)) -> dict:
    try:
        if patient.patient_id:
            PatientDAO.delete(patient_id=patient.patient_id)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def validate_patient_info(patient_info: PatientCreateRequest) -> bool:
    # all fields are required; password must meet complexity rules; cin must be 8 digits
    if (
        not patient_info.first_name or
        not patient_info.last_name or
        not patient_info.username or
        not patient_info.gender or
        patient_info.gender.lower() not in {"male", "female"} or
        not patient_info.date_of_birth
    ):
        return False
    if PatientDAO.username_exists(patient_info.username):
        raise HTTPException(status_code=420, detail="Username already exists")
    if PatientDAO.cin_exists(patient_info.cin):
        raise HTTPException(status_code=420, detail="CIN already exists")
    if not validate_password(patient_info.password):
        raise HTTPException(status_code=420, detail="password must contain at least 8 characters, 1 uppercase letter, 1 number, and 1 special character")
    return True

#***************************************************************************************************************
#***************************************************************************************************************
#................................................SESSIONS.......................................................
#***************************************************************************************************************
#***************************************************************************************************************

@app.get("/thread/{thread_id}/messages")
def get_patient_session(thread_id: int,payload: dict = Depends(verify_psychiatrist_token)):
    try:
        thread = PatientThreadDAO.get(thread_id=thread_id)
        threads_dict = thread.to_dict(orient="records")[0]

        patient_id = threads_dict["patient_id"]

        patient_context = PatientContext(user_id=patient_id, thread_id=str(thread_id))
        conversation_history = SymptomExtractionAgent.get_previous_conversation_readonly(patient_context)

        # strip the exit code marker from the last message so the frontend never sees it
        exit_code = os.getenv("EXIT_CODE_END_OF_CONVERSATION")

        if conversation_history:
            conversation_history[-1].content = (
                conversation_history[-1].content.replace(exit_code, "").strip()
            )

        return conversation_history
    except JWTError:
        raise HTTPException(status_code=401,)

@app.get("/thread/{thread_id}")
def get_thread(thread_id: int,payload: dict = Depends(verify_psychiatrist_token)) -> dict:
    try:
        thread = PatientThreadDAO.get(thread_id=thread_id)
        return thread.to_dict(orient="records")[0]
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

@app.delete("/thread")
def delete_thread(request: ThreadDeleteRequest, payload: dict = Depends(verify_psychiatrist_token)):
    try:
        PatientThreadDAO.delete(thread_id=request.thread_id)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

@app.post("/patient/symptom")
def add_patient_symptom(request: AddPatientSymptomsRequest, payload: dict = Depends(verify_psychiatrist_token)):
    try:
        PatientSymptomDAO.insert(
            patient_id=request.patient_id,
            thread_id=str(request.thread_id),
            symptom_id=request.symptom_id,
            confidence=SymptomLikelihood.CONFIRMED
        )
        return True
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

@app.post("/patient/disorder")
def add_patient_disorder(request: AddPatientDisorderRequest, payload: dict = Depends(verify_psychiatrist_token)):
    try:
        PatientDisorderDAO.insert(
            patient_id=request.patient_id,
            thread_id=str(request.thread_id),
            confidence=0.9,
            disorder_id=request.disorder_id,
            diagnosed_at=datetime.datetime.now()
        )
        return True
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

@app.post("/session")
def add_session(request: AddSessionRequest, payload: dict = Depends(verify_psychiatrist_token)):
    try:
        thread_id = PatientThreadDAO.add_thread(
            patient_id=request.patient_id,
            additional_info=request.additional_info,
            stage_of_diagnosis="START"
        )
        for symptom_id in request.symptoms:
            PatientSymptomDAO.insert_or_update_max_confidence(
                patient_id=request.patient_id,
                symptom_id=symptom_id,
                thread_id=str(thread_id),
                confidence=SymptomLikelihood.CONFIRMED
            )
        for disorder_id in request.disorders:
            PatientDisorderDAO.insert(
                patient_id=request.patient_id,
                disorder_id=disorder_id,
                thread_id=str(thread_id),
                diagnosed_at=datetime.datetime.now(),
                confidence=0.8
            )
        return True
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

#***************************************************************************************************************
#***************************************************************************************************************
#................................................REFERENCE......................................................
#***************************************************************************************************************
#***************************************************************************************************************
@app.get("/disorders")
def get_all_disorders_info(payload: dict = Depends(verify_psychiatrist_token)):
    try:
        return DisorderDAO.get_all_with_symptoms()
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


#***************************************************************************************************************
#***************************************************************************************************************
#.................................................PROFILE.......................................................
#***************************************************************************************************************
#***************************************************************************************************************

@app.get("/profile")
def get_psychologist_profile(payload: dict = Depends(verify_psychiatrist_token))->dict:
    try:
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

@app.patch("/profile/pwd")
def update_password(request: PsychiatristUpdatePasswordRequest,payload: dict = Depends(verify_psychiatrist_token))->None:
    try:
        if request.old_password != payload["password"]:
            raise HTTPException(status_code=411, detail="wrong original password")
        if not validate_password(request.new_password):
            raise HTTPException(status_code=412, detail="invalid password format")
        PsychiatristDAO.update(
            psych_id=payload["id"],
            password=request.new_password
        )
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


#***************************************************************************************************************
#***************************************************************************************************************
#.................................................ADMINS........................................................
#***************************************************************************************************************
#***************************************************************************************************************


@app.get("/all_psychiatrists")
def get_all_psychiatrists(payload: dict = Depends(verify_admin_token)):
    try:
        return PsychiatristDAO.get_all().to_dict(orient="records")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

@app.delete("/psychiatrist")
def delete_psychiatrist(request: PsychiatristDeleteRequest,payload: dict = Depends(verify_admin_token)):
    try:
        PsychiatristDAO.delete(
            psych_id=request.psy_id
        )
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

@app.patch("/psychiatrist/verification")
def update_psychiatrist_verification_status(request: UpdatePsychiatristVerificationStatusRequest,payload: dict = Depends(verify_admin_token)):
    try:
        PsychiatristDAO.update(
            psych_id=request.psych_id,
            account_verified=request.account_verified
        )
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


@app.patch("/psychiatrist/access")
def update_psychiatrist_access_level(request: UpdatePsychiatristAccessLevelRequest,payload: dict = Depends(verify_admin_token)):
    try:
        if request.psy_type != "ADMIN" and request.psy_type!= "PSY":
            raise HTTPException(status_code=420, detail="Invalid access level")
        PsychiatristDAO.update(
            psych_id=request.psych_id,
            psy_type=request.psy_type
        )
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


#***************************************************************************************************************
#***************************************************************************************************************
#..............................................MOBILE_APP.......................................................
#***************************************************************************************************************
#***************************************************************************************************************

def generate_patient_token(patient: DataFrame)->str:
    patient["date_of_birth"] = patient["date_of_birth"].astype(str)  # change the formatting of the date for compatibility with JWT
    patient["created_at"] = patient["created_at"].astype(str)

    payload = patient.to_dict(orient="records")[0]
    payload["exp"] = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=7)
    key = os.getenv('JWT_SECRET_KEY_PATIENT')
    token = jwt.encode(
        claims=payload,
        key=key,
        algorithm=os.getenv('JWT_ALGORITHM')
    )
    return token

def verify_patient_token(authorization: str = Header()):
    try:
        payload = jwt.decode(
            token=authorization,
            key=os.getenv('JWT_SECRET_KEY_PATIENT'),
            algorithms=os.getenv('JWT_ALGORITHM')
        )
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


@app.post("/patient/login")
def patient_login(request: PatientLoginRequest)->dict:
    patient_df = PatientDAO.get_by_username_password(
        username=request.username,
        password=request.password
    )
    if patient_df.empty:
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    token = generate_patient_token(patient_df)
    return {"token": token}

@app.post("/patient/validate_token")
def validate_patient_token(payload: dict = Depends(verify_patient_token)):
    try:
        return {"message": "valid token"}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

@app.get("/patient_sessions")
def get_patient_sessions(payload: dict = Depends(verify_patient_token)):
    try:
        patient_id = payload["patient_id"]
        sessions_df = PatientThreadDAO.get_by_patient_id(patient_id=patient_id)
        sessions_df["created_at"] = pd.to_datetime(sessions_df["created_at"])
        sessions_df.drop(columns=["diagnosis_id", "additional_info"], inplace=True)
        return sessions_df.to_dict(orient="records") if not sessions_df.empty else []
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

@app.get("/patient_profile_info")
def get_patient_profile_info(payload: dict = Depends(verify_patient_token)):
    try:
        patient_id = payload["patient_id"]
        patient_df = PatientDAO.get(patient_id=patient_id)
        patient_df.drop(columns=["patient_id", "created_at", "password"], inplace=True)
        return patient_df.to_dict(orient="records")[0] if not patient_df.empty else {}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

@app.get("/patient_thread/{thread_id}")
def get_patient_thread(thread_id: int):
    try:
        thread = PatientThreadDAO.get(thread_id=thread_id)
        threads_dict = thread.to_dict(orient="records")[0]

        patient_id = threads_dict["patient_id"]

        patient_context = PatientContext(user_id=patient_id, thread_id=str(thread_id))
        conversation_history = SymptomExtractionAgent.get_previous_conversation_readonly(patient_context)

        # strip the exit code marker from the last message so the frontend never sees it
        exit_code = os.getenv("EXIT_CODE_END_OF_CONVERSATION")

        print(exit_code)

        if conversation_history:
            conversation_history[-1].content = (
                conversation_history[-1].content.replace(exit_code, "").strip()
            )

        return conversation_history
    except JWTError:
        raise HTTPException(status_code=401,)



@app.post("/patient_send_message")
async def send_chat_message(request: PatientChatRequest, payload: dict = Depends(verify_patient_token)):
    try:
        patient_id = payload["patient_id"]
        exit_code = os.getenv("EXIT_CODE_END_OF_CONVERSATION")

        # checking if the thread is still open
        thread_df = PatientThreadDAO.get(thread_id=request.thread_id)
        if not thread_df.iloc[0]["status"]:
            raise HTTPException(status_code=450, detail="This thread is closed")

        # prepare the agent
        context = PatientContext(
            user_id=patient_id,
            thread_id=str(request.thread_id)
        )
        agent = SymptomExtractionAgent(context=context)
         # send the message and wait for a response
        result = await asyncio.to_thread(agent.send_human_message, request.message)

        if exit_code in result.response: # checking if we reached end of conversation
            # close the thread
            PatientThreadDAO.change_status(
                thread_id=request.thread_id,
                status=False
            )

            # remove exit code
            clean_response = result.response.replace(exit_code, "").strip()

            # preparing the diagnosis agent
            messages = agent.get_previous_conversation() # retreiving all the conversation history
            diagnosis_agent = DiagnosisAgent()
            diagnosis_agent.load_patient_info(
                PatientDAO.get(patient_id=patient_id).to_dict(orient="records") # loading the patient information
            )
            diagnosis_agent.load_chat_history(messages=messages) # loading the chat history
            diagnosis_agent.load_patient_symptoms(
                PatientSymptomDAO.get_by_patient_id(patient_id=patient_id) # loading the symptoms
            )

            asyncio.create_task(generate_diagnosis(diagnosis_agent, request.thread_id))
            debug_print(clean_response)
            return {"response": clean_response, "open": False}
        debug_print(result.response)
        return {"response": result.response, "open": True}

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


async def generate_diagnosis(diagnosis_agent, thread_id):
    print("generating diagnosis ...")
    diagnosis = await asyncio.to_thread(diagnosis_agent.generate_diagnosis)  # generate diagnosis
    diagnosis_id = DiagnosisDAO.create(diagnosis)  # save diagnosis in the database
    PatientThreadDAO.update_diagnosis_id(int(thread_id), diagnosis_id)
    print("diagnosis generated")


