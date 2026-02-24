from agents.custom_agent import SymptomExtractionAgent
from models.context_classes import PatientContext

# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    context = PatientContext(
        patient_id=2
    )

    custom_agent = SymptomExtractionAgent(
        context=context,
    )

    response = custom_agent.send_message()
    print(response)
    answer = input("Youu: ")
    response2 = custom_agent.send_message(user_prompt=answer)
    print(response2)


