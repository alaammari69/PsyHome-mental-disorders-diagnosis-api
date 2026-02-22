import numpy

from ml_models.embedders import HuggingFaceEmbedder
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
    updates all db embeddings for all tables
    :return: true if no errors were encountered
    """
    embedder = HuggingFaceEmbedder.get_embedder()
    try:
        symptoms_df = SymptomDAO.get_all()

        for _,row in symptoms_df.iterrows():
            text = row["symptom_description"]
            emb = embedder.embed_query(text)
            SymptomDAO.update(row["symptom_id"], embedding= emb)
        return True
    except Exception as e:
        print(e)
        return False


update_all_db_embeddings()