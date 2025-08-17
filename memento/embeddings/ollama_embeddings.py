import os

from langchain_ollama import OllamaEmbeddings


class CustomOllamaEmbeddings(OllamaEmbeddings):
    """A wrapper for the langchain_aws.OllamaEmbeddings.

    Adds specific configuration for the project.
    """

    def __init__(self, **kwargs):
        """Initialize the OllamaEmbeddings for the project."""
        model_type_embedding, model_id_embedding = os.environ.get(
            "EMBEDDING_MODEL", "ollama:"
        ).split(":", 1)
        default_kwargs = {
            "model": model_id_embedding,
            "base_url": "http://localhost:11434",
        }

        super().__init__(**(default_kwargs | kwargs))


EmbeddingsModel = CustomOllamaEmbeddings