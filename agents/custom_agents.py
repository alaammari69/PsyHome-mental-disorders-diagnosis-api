from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain.messages import HumanMessage, SystemMessage

from agents.custom_tools import get_relevant_symptoms_data, get_patient_info
from ml_models.embedders import HuggingFaceEmbedder
from ml_models.llms import LLMModels
from models.context_classes import PatientContext
from prompts.custom_templates import symptom_extraction_prompt_template
from models.response_schemas import symptom_extraction_schema

HuggingFaceEmbedder.get_embedder()


context = PatientContext(patient_id=2)



agent = create_agent(
    model= LLMModels.get_deepseek_llm_model(),
    tools=[get_relevant_symptoms_data, get_patient_info],
    context_schema=PatientContext,
    response_format=ToolStrategy(symptom_extraction_schema)
)

conversation = {
    "messages": []
}

#chain = symptom_extraction_prompt_template | agent

user_prompt = ""
while True:

    prompt = symptom_extraction_prompt_template.format(
        conversation = conversation
    )

    response = agent.invoke({
        "messages": [SystemMessage(content=prompt)],
        },
        context=context
    )

    #response = chain.invoke(
    #    input={
    #        "conversation": conversation,
    #    }
    #)
    print(type(response["structured_response"]), response["structured_response"])
    conversation["messages"] = response["messages"]
    user_prompt = input("You: ")
    if user_prompt == "exit":
        break

    conversation["messages"].append(HumanMessage(content=user_prompt))

