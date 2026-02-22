import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_huggingface.embeddings import HuggingFaceEmbeddings


class HuggingFaceEmbedder:

    _embedder = None

    @classmethod
    def get_embedder(cls):
        """
        returns a HuggingFace embedder instance
        :return: HuggingFace embedder instance
        """
        if cls._embedder is None:

            env_path = Path(__file__).parent.parent / "core" / ".env"

            if not env_path.exists():
                raise FileNotFoundError(f".env not found at {env_path}")

            load_dotenv(dotenv_path=env_path)

            cls._embedder = HuggingFaceEmbeddings(
                model_name = os.getenv("HUGGINGFACE_MODEL_NAME")
            )
        return cls._embedder

