from dataclasses import dataclass


@dataclass
class PatientContext:
    user_id: int
    thread_id: str
    #previous_symptoms: str
    #previous_diagnoses: str