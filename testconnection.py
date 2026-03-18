import datetime

from sqlalchemy import Date

from models.response_schemas import ExtractedSymptomSchema
from repository.patient_disorders_dao import PatientDisorderDAO
from repository.patient_symptoms_dao import PatientSymptomDAO
from agents.custom_tools import get_related_undiagnosed_symptoms_and_disorders
from rich import print

data = get_related_undiagnosed_symptoms_and_disorders(id=1, symptoms=[{"symptom_id":27, "disorder_id":10}])









