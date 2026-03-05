# ONLY RUN THIS SCRIPT ONCE TO CREATE EMBEDDINGS OR TO RECREATE THE OLD ONES
# NO NEED TO CALL THE SCRIPT EACH TIME (ONLY WHEN ADDING SYMPTOM DATA TO DB FOR EXAMPLE)

from embedder.embedding_script import update_all_db_embeddings

update_all_db_embeddings()

