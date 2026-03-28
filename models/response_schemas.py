from pydantic import BaseModel, Field, conint

class SymptomExtractionAgentResponse(BaseModel):
    """schema for the extracted symptoms from the conversation with the follow-up question"""
    response: str = Field(description="The response to the patient in a format of a follow up question")