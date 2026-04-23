
import os


from rich import print

from cryptography.fernet import Fernet
from dotenv import load_dotenv

from repository.patientthreaddao import PatientThreadDAO
from repository.psychiatristsdao import PsychiatristDAO

PatientThreadDAO.add_thread(
    patient_id=2,
    thread_id=62,
    code = "efozrgrjerogrgbrghbgorgrbgr"
)