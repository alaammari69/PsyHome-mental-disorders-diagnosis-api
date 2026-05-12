from pydantic import BaseModel

class PsyLoginRequest(BaseModel):
    email: str
    password: str

class PsySignUpRequest(BaseModel):
    first_name: str
    last_name: str
    cin: str
    email: str
    password: str
    date_of_birth: str
    phone: str
    address: str
    specialization: str

class PatientCreateRequest(BaseModel):
    first_name: str
    last_name: str
    cin: str
    gender: str
    date_of_birth: str
    username: str
    password: str

class PatientUpdateRequest(PatientCreateRequest):
    patient_id: int

class PatientDeleteRequest(BaseModel):
    patient_id: int

class PsychiatristUpdatePasswordRequest(BaseModel):
    old_password: str
    new_password: str

class ThreadDeleteRequest(BaseModel):
    thread_id: int

class AddPatientSymptomsRequest(BaseModel):
    patient_id: int
    thread_id: int
    symptom_id: int

class AddPatientDisorderRequest(BaseModel):
    patient_id: int
    thread_id: int
    disorder_id: int
class AddSessionRequest(BaseModel):
    patient_id: int
    additional_info: str
    symptoms: list[int]
    disorders: list[int]

class PsychiatristDeleteRequest(BaseModel):
    psy_id: int

class UpdatePsychiatristVerificationStatusRequest(BaseModel):
    psych_id: int
    account_verified: bool

class UpdatePsychiatristAccessLevelRequest(BaseModel):
    psych_id: int
    psy_type: str

class PatientLoginRequest(BaseModel):
    username: str
    password: str

class PatientChatRequest(BaseModel):
    thread_id:int
    message: str