from pydantic import BaseModel, Field, conint


class ExtractedSymptomSchema(BaseModel):
    """the extracted symptom information"""
    symptom_id: int = Field(description="The symptom identifier of the patient from the given data")
    symptom_name: str = Field(description="The name of the symptom from the given data")
    intensity: conint(ge=0, le=10) = Field(description="How certain the symptom is from the given data")


class SaveExtractedSymptomsArgs(BaseModel):
    """Input for the tool save_extracted_symptoms"""
    extracted_symptoms: list[ExtractedSymptomSchema]