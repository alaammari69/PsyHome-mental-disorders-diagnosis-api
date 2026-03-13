import datetime

from sqlalchemy import Date

from repository.patient_disorders_dao import PatientDisorderDAO
from repository.patient_symptoms_dao import PatientSymptomDAO
from agents.custom_tools import get_related_symptoms_and_disorders
from rich import print

data = get_related_symptoms_and_disorders(id=1,symptom_ids=[1,24])
print(data)
print(len(data))








