symptom_extraction_schema = {
    "title": "extract_symptoms",
    "type": "object",
    "description": "the extracted symptoms from the conversation with the follow up question",
    "properties": {
        "extracted_symptoms": {
            "type": "array",
            "description": "list of the extracted symptoms from the conversation (could be empty if no symptoms could be diagnosed)",
            "items": {
                "type": "object",
                "properties": {
                    "symptom_id": {"type": "string", "description": "The symptom identifier of the patient from the given data"},
                    "symptom_name": {"type": "string", "description": "The name of the symptom from the given data"},
                    "symptom_existence": {"type": "number","minimum":0, "maximum":10, "description": "how certain is the existence of this symptom? (0-10)"}
                },
                "required": ["symptom_id", "symptom_name", "symptom_existence"],
                "additionalProperties": False
            }
        },
        "response": {"type": "string", "description": "The response to the patient in a format of a follow up question"},
    },
    "required": ["extracted_symptoms", "response"],
    "additionalProperties": False
}