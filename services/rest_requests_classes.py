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