import google.auth
import pandas as pd
from google.cloud.exceptions import NotFound
from google.cloud import aiplatform
from vertexai.generative_models import GenerationConfig
import vertexai
import google.generativeai as genai
import google.ai.generativelanguage as glm
from google.generativeai import caching
import streamlit as st
import os
from google.generativeai import configure
from dotenv import load_dotenv
from feedback_store import initialize_vector_table

# Load environment variables
load_dotenv()

st.set_page_config(
    page_title="TiDB.ML 🤖",
    page_icon="🤖",
)

GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
if not GOOGLE_API_KEY:
    st.error("GOOGLE_API_KEY is not set. Please check your .env file.")
    st.stop()

from utils import walkthrough, sample_questions, normalize_string, remove_sql_and_backticks, agent_prompt, intro_to_data
from toolbox import generate_sql, execute_sql, subset_churn_contribution_analysis, subset_clv_analysis, generate_visualizations, subset_shap_summary, question_reformer, customer_recommendations, model_stat, VectorDBCreator
from streamlit_utils import add_sidebar_elements, display_chat_history, handle_user_input

# Access the secret
configure(api_key=GOOGLE_API_KEY)

# Initialize the Vector Table
if not initialize_vector_table():
    st.error("Failed to initialize vector store. Some features may not work correctly.")
else:
    st.success("Vector store initialized successfully.")

# Initialize VectorDBCreator
try:
    vector_db = VectorDBCreator()
except Exception as e:
    st.error(f"Failed to initialize VectorDBCreator: {str(e)}")
    vector_db = None

# Create the Main Agent
@st.cache_resource
def get_gen_model():
    try:
        return genai.GenerativeModel(
            model_name="gemini-1.5-flash-001",
            system_instruction=agent_prompt(),
            tools=[generate_sql, execute_sql, subset_churn_contribution_analysis, subset_clv_analysis, generate_visualizations,
                   subset_shap_summary, question_reformer, customer_recommendations, model_stat],
            generation_config={"temperature": 0.3})
    except Exception as e:
        st.error(f"Failed to initialize GenerativeModel: {str(e)}")
        return None

gen_model = get_gen_model()

# Initialize chat session in session state
if "chat" not in st.session_state and gen_model is not None:
    st.session_state.chat = gen_model.start_chat(enable_automatic_function_calling=True)
if "intermediate_results" not in st.session_state:
    st.session_state.intermediate_results = {}

# Add Title
st.markdown("<h2 style='text-align: center;'>Meet TiDB.ML 🤖</h2>", unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

# Display sidebar elements
add_sidebar_elements()

display_chat_history(st.session_state.chat.history)

# Handle new user input
prompt = st.chat_input("I possess a well of knowledge. What would you like to know?")
if prompt:
    handle_user_input(prompt)