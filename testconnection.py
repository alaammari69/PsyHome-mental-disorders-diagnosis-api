
import os


from rich import print

from repository.disorderdao import DisorderDAO
from repository.patient_dao import PatientDAO
from repository.patient_disorders_dao import PatientDisorderDAO
from repository.psychiatristsdao import PsychiatristDAO



print(PatientDAO.get_all().to_dict(orient="records"))