from langchain_core.prompts import PromptTemplate

from prompts.system_prompts import symptom_extraction_prompt

symptom_extraction_prompt_template = PromptTemplate(
    input_variables=['end_signal','exit_code'],
    template=symptom_extraction_prompt,
)