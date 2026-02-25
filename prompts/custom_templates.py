from prompts import system_prompts

symptom_extraction_prompt = "\n".join([
    system_prompts.SYMPTOM_EXTRACTION_ROLE,
    system_prompts.SYMPTOM_EXTRACTION_WORKFLOW,
    system_prompts.SYMPTOM_EXTRACTION_STYLE_GUIDELINES,
    system_prompts.SYMPTOM_EXTRACTION_CRITICAL_RULES
])