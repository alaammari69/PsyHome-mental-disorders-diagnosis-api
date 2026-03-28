from dataclasses import dataclass
from enum import Enum

from pydantic import BaseModel, Field, conint


@dataclass
class Symptom:
    symptom_id: int
    symptom_name: str
    symptom_description: str
    disorder_id: int

@dataclass
class Disorder:
    disorder_id: int
    category_id: int
    disorder_name: str
    dsm_code: str
    parent_disorder_id: int|None
    is_subtype: bool

class StageOfDiagnosis(Enum):
    START = 1
    SYMPTOM_EXTRACTION = 2
    DIAGNOSIS = 3

class ExtractedSymptomSchema(BaseModel):
    """the extracted symptom information"""
    symptom_id: int = Field(description="The symptom identifier of the patient from the given data")
    symptom_name: str = Field(description="The name of the symptom from the given data")
    symptom_confidence: str = Field(description="""The how certain is the symptom from the given data   - ABSENT    → patient explicitly denied it
  - UNLIKELY  → patient seems to contradict or push back against it
  - NEUTRAL   → unclear, ambiguous, or patient is unsure
  - LIKELY    → implied by tone, context, or partially confirmed
  - CONFIRMED → explicitly and clearly stated by the patient""")

class PatientContext:

    # those values are not going to be changed once created a Patient context instance
    patient_id: int
    thread_id: str

    # these values keep changing according to the conversation with the agents
    user_text: str
    relevant_symptoms_data: list[Symptom]
    new_extracted_symptoms: list[ExtractedSymptomSchema]
    possible_related_disorders: list[Disorder]
    possible_related_symptoms: list[Symptom]
    expected_symptom: Symptom

    # no use (yet)
    stage_of_diagnosis: StageOfDiagnosis


    def __init__(self, user_id:int, thread_id:str):
        self.patient_id = user_id # for identifying the patient
        self.thread_id = thread_id # for identifying the thread of what chat history
        self.new_extracted_symptoms = [] # for temporarily saving the confirmed extracted symptoms by the agent
        self.possible_related_disorders = [] # for keeping track of SUSPECTED disorders
        self.possible_related_symptoms = [] # for keeping track of SUSPECTED symptoms
        self.expected_symptom = None # idk how to explain currently
        self.user_text = "" # the last message that the user sent to the agent
        self.relevant_symptoms_data = [] # the symptoms which the agent is going to pick from that are present in the patient
        self.stage_of_diagnosis = StageOfDiagnosis.START


