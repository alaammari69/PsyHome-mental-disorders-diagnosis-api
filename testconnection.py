import datetime

from repository.patient_dao import PatientDAO



PatientDAO.insert(
    "testing",
    "testing",
    "abc",
    date_of_birth=datetime.date(1999,10,10),
    gender="male",
)


