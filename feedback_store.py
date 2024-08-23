import os
import yaml
from dotenv import load_dotenv
from langchain_community.vectorstores import TiDBVectorStore
from langchain_google_genai import GoogleGenerativeAIEmbeddings
import logging
import time
from tenacity import retry, stop_after_attempt, wait_fixed

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables and configuration
load_dotenv()
with open('llm_configs.yml', 'r') as f:
    llm_config = yaml.safe_load(f)

tidb_connection_string = os.getenv('TIDB_CONNECTION_URL')
google_api_key = os.getenv('GOOGLE_API_KEY')

# Initialize Google embedding model
embeddings = GoogleGenerativeAIEmbeddings(model=llm_config['embedding_model'], google_api_key=google_api_key)

@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def get_vector_store(table_name):
    global vector_store
    try:
        if vector_store is None or not vector_store.is_connected():
            store = TiDBVectorStore(
                embedding_function=embeddings,
                connection_string=tidb_connection_string,
                table_name=table_name,
            )
            vector_store = store
            logger.info(f"Connected to vector store: {table_name}")
        return vector_store
    except Exception as e:
        logger.error(f"Error connecting to vector store: {str(e)}")
        vector_store = None
        raise

# Add a method to check connection
def is_connected(self):
    try:
        # Perform a simple query to check connection
        self.client.execute("SELECT 1")
        return True
    except Exception:
        return False

# Monkey patch the TiDBVectorStore class to add the is_connected method
TiDBVectorStore.is_connected = is_connected

# Global variable to store the vector store instance
vector_store = None

def store_feedback(question, answer, feedback):
    logger.info(f"Storing feedback - Question: {question[:50]}... Feedback: {feedback}")
    table_name = llm_config.get('feedback_table', 'feedback_store')
    db = get_vector_store(table_name)
    if db is None:
        return False
    try:
        db.add_texts(
            texts=[question],
            metadatas=[{"answer": answer, "feedback": feedback}]
        )
        logger.info("Feedback stored successfully")
        return True
    except Exception as e:
        logger.error(f"Error storing feedback: {str(e)}")
        return False

def get_similar_question_answer(question, k=1):
    logger.info(f"Searching for similar question: {question[:50]}...")
    table_name = llm_config.get('feedback_table', 'feedback_store')
    db = get_vector_store(table_name)
    if db is None:
        return None
    try:
        results = db.similarity_search_with_score(question, k=k,filter={"feedback":1})
        if results:
            similar_docs = []
            for doc, score in results:
                similar_docs.append({
                    "question": doc.page_content,
                    "answer": doc.metadata.get("answer"),
                    "feedback": doc.metadata.get("feedback"),
                    "distance": score  # This is cosine distance, lower is more similar
                })
            logger.info(f"Found {len(similar_docs)} similar questions")
            return similar_docs
        else:
            logger.info("No similar questions found.")
            return None
    except Exception as e:
        logger.error(f"Error retrieving similar questions: {str(e)}")
        return None

def initialize_vector_table():
    table_name = llm_config.get('feedback_table', 'feedback_store')
    max_retries = 3
    retry_delay = 5  # seconds

    for attempt in range(max_retries):
        try:
            db = get_vector_store(table_name)
            if db is not None:
                logger.info(f"Vector table {table_name} initialized successfully")
                return True
            else:
                logger.warning(f"Failed to initialize vector table {table_name}. Retrying...")
        except Exception as e:
            logger.error(f"Error initializing vector table: {str(e)}")
        
        if attempt < max_retries - 1:
            logger.info(f"Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)
    
    logger.error(f"Failed to initialize vector table {table_name} after {max_retries} attempts")
    return False