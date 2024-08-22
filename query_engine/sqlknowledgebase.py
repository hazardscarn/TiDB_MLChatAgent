import os
import csv
from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import TiDBVectorStore
from sqlalchemy import create_engine, text
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
tidb_connection_string = os.getenv('TIDB_CONNECTION_URL')
google_api_key = os.getenv('GOOGLE_API_KEY')

# Initialize Google embedding model
embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004", google_api_key=google_api_key)

TABLE_NAME = "known_good_sqlbase_vector"

class VectorDBCreator:
    def __init__(self):
        self.engine = create_engine(tidb_connection_string)
        self.vector_store = self.load_existing_vector_store()

    def load_existing_vector_store(self):
        try:
            vector_store = TiDBVectorStore.from_existing_vector_table(
                embedding=embeddings,
                connection_string=tidb_connection_string,
                table_name=TABLE_NAME
            )
            logger.info("Existing vector store loaded successfully.")
            return vector_store
        except Exception as e:
            logger.warning(f"Failed to load existing vector store: {e}")
            return None

    def create_or_update_vector_store(self, texts, metadatas):
        if self.vector_store:
            # Add new documents
            self.vector_store.add_texts(texts=texts, metadatas=metadatas)
            logger.info(f"Added {len(texts)} new entries to the existing vector store.")
        else:
            # Create new vector store
            self.vector_store = TiDBVectorStore.from_texts(
                texts=texts,
                embedding=embeddings,
                metadatas=metadatas,
                connection_string=tidb_connection_string,
                table_name=TABLE_NAME,
                distance_strategy="cosine"
            )
            logger.info(f"Created new vector store with {len(texts)} entries.")

    def load_and_embed_data(self, csv_file_path):
        try:
            texts = []
            metadatas = []

            with open(csv_file_path, 'r') as file:
                csv_reader = csv.DictReader(file)
                for row in csv_reader:
                    texts.append(row['question'])
                    metadatas.append({"sql_answer": row['sql']})

            self.create_or_update_vector_store(texts, metadatas)
            logger.info(f"Data loaded and embedded successfully. {len(texts)} rows processed.")
            self.verify_data_insertion(len(texts))
        except FileNotFoundError:
            logger.error(f"CSV file not found: {csv_file_path}")
            raise
        except Exception as e:
            logger.error(f"Error loading and embedding data: {e}")
            raise

    def verify_data_insertion(self, expected_count):
        try:
            with self.engine.connect() as connection:
                result = connection.execute(text(f"SELECT COUNT(*) FROM {TABLE_NAME}")).fetchone()
                actual_count = result[0] if result else 0
                if actual_count >= expected_count:
                    logger.info(f"Data insertion verified. {actual_count} rows in the table.")
                else:
                    logger.warning(f"Data insertion mismatch. Expected at least {expected_count} rows, found {actual_count} rows.")
                
                # Fetch and log a sample row
                sample = connection.execute(text(f"SELECT * FROM {TABLE_NAME} LIMIT 1")).fetchone()
                if sample:
                    logger.info(f"Sample row: {sample}")
                else:
                    logger.warning("No sample row found.")
        except Exception as e:
            logger.error(f"Error verifying data insertion: {e}")

    def find_similar_questions(self, query, top_k=3):
        if not self.vector_store:
            logger.error("Vector store not initialized. Unable to find similar questions.")
            return [], False

        try:
            # First, try to find an exact match
            exact_matches = self.vector_store.similarity_search_with_score(
                query, k=1, filter={"question": query}
            )
            
            if exact_matches:
                exact_match = exact_matches[0]
                logger.info(f"Exact match found for query: {query}")
                return exact_match[0].metadata["sql_answer"], True

            # If no exact match, find similar questions
            similar_questions = self.vector_store.similarity_search_with_score(query, k=top_k)
            
            results = [
                (doc.page_content, doc.metadata["sql_answer"], score)
                for doc, score in similar_questions
            ]

            logger.info(f"Found {len(results)} similar questions for query: {query}")
            return results, False
        except Exception as e:
            logger.error(f"Error finding similar questions: {e}")
            raise

# Global instance for retrieval mode
vector_db = VectorDBCreator()

def main():
    # This function is used for the initial creation of the vector database
    vector_db_creator = VectorDBCreator()
    
    # Load and embed data from CSV
    csv_file_path = 'data/telecom_churn/known_good_sqlbase.csv'
    vector_db_creator.load_and_embed_data(csv_file_path)

    # Example usage of find_similar_questions
    query = "What is the average monthly charges for customers who have churned?"
    result, is_exact_match = vector_db_creator.find_similar_questions(query)

    if is_exact_match:
        logger.info(f"Exact match found. SQL answer: {result}")
    else:
        logger.info("Similar questions found:")
        for question, sql_answer, similarity in result:
            logger.info(f"Question: {question}")
            logger.info(f"SQL Answer: {sql_answer}")
            logger.info(f"Similarity: {similarity}")
            logger.info("---")

if __name__ == "__main__":
    main()