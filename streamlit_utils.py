import streamlit as st
from utils import walkthrough,sample_questions,intro_to_data,banner
import time
import yaml
from feedback_store import store_feedback, get_similar_question_answer
import logging
import uuid
import time


logger = logging.getLogger(__name__)


with open('conf_telchurn.yml', 'r') as f:
    model_config = yaml.load(f, Loader=yaml.FullLoader)

# Function to map roles to Streamlit roles
def role_to_streamlit(role):
    return "assistant" if role == "model" else role

# Function to add sidebar elements
def add_sidebar_elements():
    linkedin_url = "https://www.linkedin.com/in/david-babu-15047096/"
    ko_fi_url = "https://ko-fi.com/Q5Q0V3AJA"

    icons_html = f"""
    <div style="display: flex; align-items: center; justify-content: center; gap: 20px; margin-left: auto; margin-right: auto; max-width: fit-content;">
        <a href="{ko_fi_url}" target="_blank">
            <img height="36" style="border:0px;height:36px;" src="https://storage.ko-fi.com/cdn/kofi2.png?v=3" border="0" alt="Buy Me a Coffee at ko-fi.com" />
        </a>
        <a href="{linkedin_url}" target="_blank">
            <img src="https://upload.wikimedia.org/wikipedia/commons/e/e9/Linkedin_icon.svg" alt="LinkedIn" style="width: 30px; height: 30px;">
        </a>
    </div>
    """
    st.sidebar.markdown("<br>", unsafe_allow_html=True)
    st.sidebar.markdown("<br>", unsafe_allow_html=True)
    with st.sidebar.expander("Click here for a short introduction to know what I can do for you"):
        st.markdown(walkthrough())
    st.sidebar.markdown("<br>", unsafe_allow_html=True)
    with st.sidebar.expander("Click here to see some sample questions I can help you with"):
        st.markdown(sample_questions())
    st.sidebar.markdown("<br>", unsafe_allow_html=True)
    with st.sidebar.expander("Click here to get an Introduction to Data and Model behind the wraps"):
        st.markdown(intro_to_data(model_config))
    st.sidebar.markdown("<br>", unsafe_allow_html=True)
    st.sidebar.markdown("<br>", unsafe_allow_html=True)
    banner()
    with st.sidebar:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(icons_html, unsafe_allow_html=True)

def display_chat_history(chat_history):
    for message in chat_history:
        role = role_to_streamlit(message.role)
        parts = message.parts
        
        for part in parts:
            if "text" in part:
                if part.text and part.text.strip():
                    with st.chat_message(role):
                        st.write(part.text)




# Directly inject custom CSS to make expander header text darker
st.markdown(
    """
    <style>
    /* Make sidebar expander header text darker */
    .stSidebar .st-expander .st-expanderHeader {
        color: #1a1a1a !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)



# # Function to handle new user input and get response from the model
# def handle_user_input(prompt):
#     # Display user's message
#     st.chat_message("user").markdown(prompt)

#     with st.spinner("Processing..."):
#         # Send user entry to Gemini and get the response
#         response = st.session_state.chat.send_message(prompt)
#         # Assuming response.candidates[0].content.parts is a list of text parts
#         parts = response.candidates[0].content.parts[0].text

#     # Placeholder for the assistant's response
#     response_container = st.chat_message("assistant")
#     response_placeholder = response_container.empty()
#     response_text = ""

#     # Simulate streaming each character
#     for char in parts:
#         response_text += char
#         response_placeholder.markdown(response_text)
#         time.sleep(0.005)  # Simulate streaming delay for demonstration purposes



def handle_user_input(prompt):
    logger.info(f"Received user input: {prompt}")

    # Display user's message
    st.chat_message("user").markdown(prompt)

    # Check for similar questions first
    similar_questions = get_similar_question_answer(prompt, k=1)
    print(f"Debug - Similar questions: {similar_questions}")
    
    if similar_questions:
        similar_question = similar_questions[0]
        distance = similar_question['distance']
        feedback_score = similar_question.get('feedback', 'N/A')
        
        # Check for exact match by comparing strings
        if prompt.lower().strip() == similar_question['question'].lower().strip():
            st.info(f"This exact question was found in our vector DB with a feedback score of {feedback_score}. Here's the answer:")
            display_answer(prompt, similar_question['answer'], is_similar=True)
        elif distance < 0.16:  # Similar question (adjust threshold as needed)
            st.info(f"A similar question was found in our vector DB with a feedback score of {feedback_score}. Here's the answer:")
            display_answer(prompt, similar_question['answer'], is_similar=True)
            st.warning("If this answer doesn't address your question, please use the 'Use Agent' button below to get a new response.")
            
            # # Use a button to trigger agent response
            # if st.button("Use Agent"):
            #     generate_new_response(prompt)
        else:
            generate_new_response(prompt)
    else:
        generate_new_response(prompt)

def generate_new_response(prompt):
    with st.spinner("Processing with AI agent..."):
        # Send user entry to Gemini and get the response
        response = st.session_state.chat.send_message(prompt)
        answer = response.candidates[0].content.parts[0].text
    
    display_answer(prompt, answer)

def display_answer(prompt, answer, is_similar=False):
    response_container = st.chat_message("assistant")
    response_placeholder = response_container.empty()
    response_text = ""
    print(f"Debug - Displaying answer: {answer[:100]}...")  # Print first 100 chars of answer

    # Simulate streaming each character
    for char in answer:
        response_text += char
        response_placeholder.markdown(response_text)
        time.sleep(0.005)  # Simulate streaming delay for demonstration purposes

    # Only add feedback buttons for new responses
    if not is_similar:
        add_feedback_buttons(prompt, answer)

def add_feedback_buttons(question, answer):
    qa_key = str(uuid.uuid4())

    def on_feedback_click(feedback_value):
        logger.info(f"Feedback button clicked: {feedback_value}")
        if store_feedback(question, answer, feedback_value):
            st.success("Thank you for your feedback!")
            logger.info(f"Feedback stored successfully: {feedback_value}")
        else:
            st.error("Failed to store feedback. Please try again.")
            logger.error(f"Failed to store feedback: {feedback_value}")

    col1, col2, col3 = st.columns([1,1,3])

    with col1:
        st.button("👍", key=f"like_{qa_key}", on_click=on_feedback_click, args=(1,))
    with col2:
        st.button("👎", key=f"dislike_{qa_key}", on_click=on_feedback_click, args=(-1,))
    with col3:
        st.write("")  # Empty column for spacing