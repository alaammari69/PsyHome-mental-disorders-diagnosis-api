from pydantic import BaseModel, Field, conint

from models.context_classes import ExtractedSymptomSchema


class SaveExtractedSymptomsArgs(BaseModel):
    """Input for the tool save_extracted_symptoms"""
    extracted_symptoms: list[ExtractedSymptomSchema]