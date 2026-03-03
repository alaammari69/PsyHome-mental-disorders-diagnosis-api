from langchain_core.messages import HumanMessage

from agents.custom_agents import SymptomExtractionAgent
from models.context_classes import PatientContext

from dotenv import load_dotenv
from rich import print

load_dotenv()

# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    context = PatientContext(
        user_id=1,
        session_id="7",
    )

    custom_agent = SymptomExtractionAgent(
        context=context,
    )

    messages = custom_agent.get_all_messages()
    print(type(messages))
    if messages is not None:
        for msg in messages:
            print(msg.content)

    result = custom_agent.send_system_message("Greet the patient and ask how he's doing")
    print(result.extracted_symptoms)
    print(result.response)
    while True:

        user_message = input("You: ")
        if user_message == "exit":
            break
        result = custom_agent.send_human_message(user_message)
        print(result.extracted_symptoms)
        print(result.response)
