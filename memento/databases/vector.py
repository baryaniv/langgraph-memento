import os
import uuid

from langchain_core.documents import Document
from langchain_postgres import PGVector
from langchain_text_splitters import RecursiveCharacterTextSplitter

from ..embeddings.ollama_embeddings import EmbeddingsModel

from .. import env


class Vector:
    def __init__(self):
        """Initialize the database connection."""

        super().__init__()

        # self.user = os.environ.get("POSTGRES_USER", "postgres")
        # self.password = os.environ["POSTGRES_PASSWORD"]
        # self.host = os.environ.get("POSTGRES_HOSTNAME", "postgres")
        # self.port = os.environ.get("POSTGRES_PORT", 54321)
        # self.database = os.environ.get("POSTGRES_DATABASE", "postgres")
        # auth = f"{self.user}:{self.password}"
        self.uri = env.POSTGRES_URL
        collection_name = "my_docs"

        self.vector_store = PGVector(
            embeddings=EmbeddingsModel(),
            collection_name=collection_name,
            connection=self.uri,
            use_jsonb=True,
        )

        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            is_separator_regex=False,
        )

    def get_similarity_search_results(self, text: str, top_k: int = 5):
        results = self.vector_store.similarity_search(text, k=top_k)
        return results

    def add_documents(self, docs):
        self.vector_store.add_documents(
            docs, ids=[str(doc.metadata["id"]) for doc in docs]
        )

    def add_semantic_json(self, semantic_json):
        docs = []
        doc_id = 1

        for table in semantic_json:
            # Create a document for the table itself
            table_content = f"""
            טבלה: {table["table_display_name"]} ({table["table_name"]})
            {table["table_desc"]}
            {table["table_domain"]}
            """

            # Include the whole table data in metadata for table documents
            table_metadata = {
                "id": str(uuid.uuid4()),
                "type": "table",
                "table_name": table["table_name"],
                "table_display_name": table["table_display_name"],
                "table_desc": table["table_desc"],
                "table_domain": table["table_domain"],
                "is_dimension": table["is_dimension"],
                "whole_table": table,  # Include entire table data
            }

            # Split table content if it's too long
            table_chunks = self.text_splitter.split_text(table_content.strip())

            for chunk_idx, chunk in enumerate(table_chunks):
                chunk_metadata = table_metadata.copy()
                chunk_metadata["id"] = str(uuid.uuid4())
                chunk_metadata["chunk_index"] = chunk_idx
                chunk_metadata["total_chunks"] = len(table_chunks)

                docs.append(Document(page_content=chunk, metadata=chunk_metadata))
                doc_id += 1

            # Create documents for each column
            for column in table["columns"]:
                column_content = f"""
                עמודה: {column["column_display_name"]} {column["col_name"]} {column["col_description"]}
                טבלה: {table["table_display_name"]} {table["table_name"]}
                """

                # Include whole table and specific column in metadata for column documents
                column_metadata = {
                    "id": str(uuid.uuid4()),
                    "type": "column",
                    "table_name": table["table_name"],
                    "table_display_name": table["table_display_name"],
                    "table_desc": table["table_desc"],
                    "table_domain": table["table_domain"],
                    "col_name": column["col_name"],
                    "column_display_name": column["column_display_name"],
                    "col_description": column["col_description"],
                    "col_type": column["col_type"],
                    "business_attribute": column.get("business_attribute", None),
                    "whole_table": table,  # Include entire table data
                    "column_data": column,  # Include specific column data
                }

                # Split column content if it's too long
                column_chunks = self.text_splitter.split_text(column_content.strip())

                for chunk_idx, chunk in enumerate(column_chunks):
                    chunk_metadata = column_metadata.copy()
                    chunk_metadata["id"] = str(uuid.uuid4())
                    chunk_metadata["chunk_index"] = chunk_idx
                    chunk_metadata["total_chunks"] = len(column_chunks)

                    docs.append(Document(page_content=chunk, metadata=chunk_metadata))
                    doc_id += 1
            self.add_documents(docs)
        return {
            "results": "ok",
            "tables_processed": len(semantic_json),
            "documents_created": len(docs),
        }