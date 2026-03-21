from dataclasses import dataclass


@dataclass
class PatientContext:
    user_id: int
    thread_id: str
    possible_related_disorders: list[dict]
    possible_related_symptoms: list[dict]

    commited_symptom_id_for_making_sure: dict

    last_user_text: str

    def __init__(self, user_id:int, thread_id:str):
        self.user_id = user_id # for identifying the patient
        self.thread_id = thread_id # for identifying the thread of what chat history
        self.possible_related_disorders = [] # for keeping track of SUSPECTED disorders
        self.possible_related_symptoms = [] # for keeping track of SUSPECTED symptoms
        self.commited_symptom_id_for_making_sure = {} # idk how to explain currently
        self.last_user_text = "" # the last message that the user sent to the agent