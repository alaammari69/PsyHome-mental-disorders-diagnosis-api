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
