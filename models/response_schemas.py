from pydantic import BaseModel, Field
from datetime import datetime

from models.context_classes import Disorder, Symptom


class SymptomExtractionAgentResponse(BaseModel):
    """schema for the extracted symptoms from the conversation with the follow-up question"""
    response: str = Field(description="The response to the patient in a format of a follow up question")


class ExtractedDisorder(BaseModel):
    disorder_id: int
    percentage: float = Field(description="Confidence percentage 0.0-100.0")
    explanation: str = Field(description="Clinical reasoning based on the patient's symptoms")
    supporting_symptoms_IDs: list[int] = Field(description="symptoms that support this diagnosis")
    contradicting_symptoms_IDs: list[int] = Field(description="symptoms that contradict or were ABSENT/UNLIKELY")

class DiagnosisAgentResponse(BaseModel):
    """schema for the output of the diagnosis agent"""

    # patient info
    patient_id: int = Field(description="Patient id")

    # diagnosis
    extracted_disorders: list[ExtractedDisorder] = Field(description="2-4 possible disorders ranked by percentage. The sum of all percentages must not exceed 100.0.")
    overall_confidence: float = Field(description="Overall confidence in the diagnosis 0.0-100.0")
    clinical_summary: str = Field(description="A brief narrative summary of the patient's presentation")
    recommended_followup: str = Field(description="What should be explored further in future sessions")
    date_of_diagnosis: datetime = Field(default_factory=datetime.now)



