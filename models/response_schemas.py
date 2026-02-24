from pydantic.v1 import BaseModel, Field, conint

class ExtractedSymptomSchema(BaseModel):
    """the extracted symptom information"""
    symptom_id: str = Field(description="The symptom identifier of the patient from the given data")
    symptom_name: str = Field(description="The name of the symptom from the given data")
    symptom_existence: conint(ge=0, le=10) = Field(description="The how certain is the symptom from the given data",)

class SymptomExtractionAgentResponse(BaseModel):
    """schema for the extracted symptoms from the conversation with the follow-up question"""
    response: str = Field(description="The response to the patient in a format of a follow up question")
    extracted_symptoms : list[ExtractedSymptomSchema] = Field(description="list of the extracted symptoms from the conversation (could be empty if no symptoms could be extracted)")