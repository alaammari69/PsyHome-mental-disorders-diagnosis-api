import datetime

from sqlalchemy import Date

from repository.patient_disorders_dao import PatientDisorderDAO
from repository.patient_symptoms_dao import PatientSymptomDAO




PatientSymptomDAO.insert_or_update_max_intensity(
    patient_id=1,
    symptom_id=37,
    thread_id="8",
    intensity=8
)
print(PatientSymptomDAO.get_by_patient_symptom_thread_id(
    patient_id=1,
    symptom_id=37,
    thread_id="8"
))




