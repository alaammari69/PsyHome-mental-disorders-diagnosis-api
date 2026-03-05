import datetime

from repository.patient_symptoms_dao import PatientSymptomDAO

PatientSymptomDAO.delete(
    patient_id=1,
    symptom_id=1,
    thread_id='1'
)
print(PatientSymptomDAO.get_all())




