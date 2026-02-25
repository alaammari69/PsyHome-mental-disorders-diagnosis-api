from agents.custom_agents import SymptomExtractionAgent
from models.context_classes import PatientContext

from dotenv import load_dotenv

load_dotenv()

# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    context = PatientContext(
        patient_id=2
    )

    custom_agent = SymptomExtractionAgent(
        context=context,
    )

    result = custom_agent.send_message()
    while True:
        print(result.extracted_symptoms)
        print(result.response)

        user_message = input("You: ")
        if user_message == "exit":
            break
        custom_agent.send_message(user_message)



