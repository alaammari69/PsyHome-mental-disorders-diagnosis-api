from agents.custom_agents import SymptomExtractionAgent
from models.context_classes import PatientContext

from dotenv import load_dotenv

load_dotenv()

# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    context = PatientContext(
        user_id=3,
        session_id=1,
    )

    custom_agent = SymptomExtractionAgent(
        context=context,
    )

    result = custom_agent.send_message("Helloo")
    print(result.extracted_symptoms)
    print(result.response)
    while True:

        user_message = input("You: ")
        if user_message == "exit":
            break
        result = custom_agent.send_message(user_message)
        print(result.extracted_symptoms)
        print(result.response)



