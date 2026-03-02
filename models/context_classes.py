from dataclasses import dataclass


@dataclass
class PatientContext:
    user_id: int
    session_id: str