import numpy as np

from repository.symptomdao import SymptomDAO
from services.embedding_script import create_embedding, update_all_db_embeddings

data = SymptomDAO.get_all()
query = ""

update_all_db_embeddings()

while query != "exit":
    query = input("Enter a query: ")
    query_embedding = create_embedding(query)

    data["dot_product"] = data["embedding"].apply(lambda x: np.dot(x, query_embedding))
    print(data[["symptom_name", "dot_product"]].sort_values(by="dot_product", ascending=False))