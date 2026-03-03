import numpy

from embedder.embedders import HuggingFaceEmbedder
from repository.symptomdao import SymptomDAO


def create_embedding(text : str)-> numpy.ndarray:
    """
    creates an embedding for a given text using HuggingFace model
    :param text: given text
    :return: embedding for given text
    """
    embedder = HuggingFaceEmbedder.get_embedder()
    return embedder.embed_query(text)

def update_all_db_embeddings()-> bool:
    """
    updates all db embeddings for all symptoms in the database
    :return: true if no errors were encountered
    """
    embedder = HuggingFaceEmbedder.get_embedder()
    try:
        symptoms_df = SymptomDAO.get_all()


        for _,row in symptoms_df.iterrows():
            # adding the name and description in one text
            text =row["symptom_name"] + ": " + row["symptom_description"]
            # create the embedding for the text
            emb = embedder.embed_query(text)
            # update the embedding column for each symptom in the db
            SymptomDAO.update(row["symptom_id"], embedding= emb)
        return True
    except Exception as e:
        print(e)
        return False