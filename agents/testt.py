
from langchain.agents import create_agent
from langchain.messages import HumanMessage
from langchain.tools import tool

from ml_models.llms import LLMModels

#this is a representation of the Data base :
profile = {
    "name": "Ala",
    "lastname": "Ammari",
    "age": 21
}


#this is a basic tool :

@tool
def get_personal_info():
    """
    this tool returns the personal info
    :return: dict with personal info
    """
    #RETREIVER
    personal_info = {
        "name": "Ala",
        "lastname": "Ammari",
        "age": 21
    }

    return personal_info

agent = create_agent(
    model= LLMModels.get_deepseek_llm_model(),
    tools=[get_personal_info]
)

response = agent.invoke({
    "messages": [HumanMessage("what is my name and age")]
})
print(response["messages"][-1].content)