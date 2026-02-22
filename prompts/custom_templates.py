from langchain_core.prompts import PromptTemplate

from prompts import system_prompts

symptom_extraction_prompt_template = PromptTemplate(
    template= system_prompts.SYMPTOM_EXTRACTION_ROLE
            +system_prompts.SYMPTOM_EXTRACTION_WORKFLOW
            +system_prompts.SYMPTOM_EXTRACTION_STYLE_GUIDELINES
            +system_prompts.SYMPTOM_EXTRACTION_CRITICAL_RULES
            +"""
                \n* Conversation : {conversation}
            """,
    input_variables=["conversation"]
)