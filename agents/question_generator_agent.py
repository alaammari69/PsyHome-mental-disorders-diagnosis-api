from langgraph.checkpoint.postgres import PostgresSaver

from  models.context_classes import PatientContext

class QuestionGeneratorAgent:
    def __init__(self, context: PatientContext, checkpointer: PostgresSaver):
        self.context = context
        self.checkpointer = checkpointer

