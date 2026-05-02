
import os


from rich import print

from cryptography.fernet import Fernet
from dotenv import load_dotenv

from agents.symptom_extraction_agent import SymptomExtractionAgent
from models.context_classes import PatientContext
from repository.diagnosisdao import DiagnosisDAO
from repository.patient_dao import PatientDAO
from repository.patientthreaddao import PatientThreadDAO
from repository.psychiatristsdao import PsychiatristDAO

print(PatientDAO.get_all().to_dict(orient='records'))