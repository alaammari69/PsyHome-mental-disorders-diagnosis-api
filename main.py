from langchain_core.messages import HumanMessage, AIMessage

from agents.symptom_extraction_agent import SymptomExtractionAgent
from models.context_classes import PatientContext

from dotenv import load_dotenv
from rich import print
from embedder.embedders import HuggingFaceEmbedder

load_dotenv()

HuggingFaceEmbedder.get_embedder()

# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    context = PatientContext(
        user_id=3,
        thread_id="36",
    )

    custom_agent = SymptomExtractionAgent(
        context=context,
    )

    messages = custom_agent.get_previous_conversation()
    print(type(messages))
    if messages is not None:
        for msg in messages:
            if type(msg) is HumanMessage:
                print(f"You: {msg.content}\n")
            if type(msg) is AIMessage:
                print(f"AI Assistant: {msg.content}\n")

    result = custom_agent.reset_session()
    print(result.response)
    while True:

        user_message = input("You: ")
        if user_message == "exit":
            break
        result = custom_agent.send_human_message(user_message)
        #print(result)
        print(f"AI Assistant: {result.response}")
