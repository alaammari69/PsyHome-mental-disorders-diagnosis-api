import datetime

from sqlalchemy import Date

from repository.patient_disorders_dao import PatientDisorderDAO
from repository.patient_symptoms_dao import PatientSymptomDAO




PatientDisorderDAO.insert(
    patient_id=1,
    disorder_id=1,
    diagnosed_at=datetime.date.today(),
    confidence=0.8,
    thread_id="8"

)




