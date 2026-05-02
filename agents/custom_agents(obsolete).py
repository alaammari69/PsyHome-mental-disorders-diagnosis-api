from langchain.messages import HumanMessage, SystemMessage

from embedder.embedders import HuggingFaceEmbedder
from ml_models.llms import LLMModels
from prompts.custom_templates import symptom_extraction_prompt_template

HuggingFaceEmbedder.get_embedder() # to create the embedder model and load it in memory

model= LLMModels.get_deepseek_llm_model(),

conversation = {
    "messages": []
}

user_prompt = ""
while True:

    prompt = symptom_extraction_prompt_template.format(
        conversation = conversation
    )

    response = model.invoke({
        "messages": [SystemMessage(content=prompt)],
        },
    )

    print(type(response["structured_response"]), response["structured_response"])
    conversation["messages"] = response["messages"]
    user_prompt = input("You: ")
    if user_prompt == "exit":
        break

    conversation["messages"].append(HumanMessage(content=user_prompt))

