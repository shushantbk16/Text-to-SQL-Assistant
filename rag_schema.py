import json
from typing import List, Dict
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.documents import Document

# Schema definitions
SCHEMA_DESCRIPTIONS = {
    "customers": "Contains customer information including unique ID, name, join date, and geographical region. Use this table to filter by customer demographics or tenure.",
    "products": "Catalog of available items. Columns include product ID, name, category (e.g., Electronics, Clothing), price, and current inventory count. Use this for product-related queries.",
    "orders": "Transactional records of purchases. Links customers to their orders. Includes order ID, customer ID, order date, and current status (e.g., Pending, Delivered).",
    "order_items": "Line items for each order. Links orders to specific products. Contains order ID, product_id, and quantity purchased. Use this to calculate total sales or product popularity."
}

class SchemaRetriever:
    def __init__(self):
        """Initialize the Schema Retriever."""
        print("Initializing Schema Retriever...")
        # Using a small, efficient model for embeddings
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        self.vector_store = self._build_vector_store()
        print("Schema Retriever Initialized.")

    def _build_vector_store(self) -> FAISS:
        """Index the schema descriptions into a FAISS vector store."""
        documents = []
        for table_name, description in SCHEMA_DESCRIPTIONS.items():
            # We embed the description, but store the table name as metadata
            doc = Document(
                page_content=description,
                metadata={"table_name": table_name}
            )
            documents.append(doc)
        
        return FAISS.from_documents(documents, self.embeddings)

    def get_relevant_tables(self, query: str, k: int = 3) -> List[str]:
        """
        Retrieve the top k most relevant tables for a given user query.
        """
        print(f"Retrieving tables for query: '{query}'")
        docs = self.vector_store.similarity_search(query, k=k)
        
        relevant_tables = [doc.metadata["table_name"] for doc in docs]
        print(f"Retrieved tables: {relevant_tables}")
        return relevant_tables

    def get_schema_string(self, table_names: List[str]) -> str:
        """
        Helper to get the DDL/Schema string for the selected tables.
        Queries the SQLite database for the actual DDL.
        """
        import sqlite3
        from setup_db import DB_NAME
        
        schema_strings = []
        try:
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            
            for table in table_names:
                # Get the CREATE TABLE statement from sqlite_master
                cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,))
                result = cursor.fetchone()
                if result:
                    schema_strings.append(result[0] + ";")
            
            conn.close()
        except Exception as e:
            print(f"Error retrieving schema: {e}")
            return ""
            
        return "\n".join(schema_strings)

if __name__ == "__main__":
    # Test the retriever
    retriever = SchemaRetriever()
    
    test_queries = [
        "Who are the customers from the North region?",
        "How many electronics did we sell?",
        "Show me the status of order #123"
    ]
    
    for q in test_queries:
        tables = retriever.get_relevant_tables(q)
        print(f"Query: {q} -> Tables: {tables}\n")
