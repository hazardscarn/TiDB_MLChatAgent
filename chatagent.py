import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import AgentExecutor, create_react_agent
from langchain.memory import ConversationBufferMemory
from langchain.tools import BaseTool
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema import SystemMessage, HumanMessage
import json

# Import your custom tools
from toolbox import (
    generate_sql, execute_sql, subset_churn_contribution_analysis,
    subset_clv_analysis, model_stat, generate_visualizations,
    question_reformer, subset_shap_summary, customer_recommendations
)

# Set up the API key
#os.environ["GOOGLE_API_KEY"] = "your-api-key-here"  # Replace with your actual API key

# Initialize the Gemini model
llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash-001")

# Set up memory
memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

# Create LangChain tools
class GenerateSQLTool(BaseTool):
    name = "Generate SQL"
    description = "Generates the SQL query based on the user question. Use this function to create a SQL query to retrieve any data user has asked for or to create an answer to user question."

    def _run(self, user_question: str):
        return generate_sql(user_question)

class ExecuteSQLTool(BaseTool):
    name = "Execute SQL"
    description = "Executes the provided SQL query and returns the result as a markdown table or JSON object. Use this only for cases where the answer to user question is directly available and further tools or processing is not required. Input should be a JSON string with keys 'user_question', 'sql_generated', and optionally 'output_mode'."

    def _run(self, input_str: str):
        input_dict = json.loads(input_str)
        user_question = input_dict['user_question']
        sql_generated = input_dict['sql_generated']
        output_mode = input_dict.get('output_mode', 'json')
        return execute_sql(user_question, sql_generated, output_mode)

class SubsetChurnContributionAnalysisTool(BaseTool):
    name = "Subset Churn Contribution Analysis"
    description = "Performs a churn contribution analysis on a subset of data. Use this function to explain the impact of a treatment on a subset of data. Input should be a JSON string with keys 'user_question' and 'sql_generated'."

    def _run(self, input_str: str):
        input_dict = json.loads(input_str)
        return subset_churn_contribution_analysis(input_dict['user_question'], input_dict['sql_generated'])

class SubsetCLVAnalysisTool(BaseTool):
    name = "Subset CLV Analysis"
    description = "Performs net effect on CLV analysis on a subset of data. Use this function to explain the impact or change in CLV if a treatment is applied on a subset of data. Input should be a JSON string with keys 'user_question', 'sql_generated', and optionally 'treatment_cost'."

    def _run(self, input_str: str):
        input_dict = json.loads(input_str)
        treatment_cost = input_dict.get('treatment_cost', 0.0)
        return subset_clv_analysis(input_dict['user_question'], input_dict['sql_generated'], treatment_cost)

class ModelStatTool(BaseTool):
    name = "Model Stats"
    description = "Returns the Model Stats to user. Use this tool for any question related to model accuracy."

    def _run(self, user_question: str):
        return model_stat(user_question)

class GenerateVisualizationsTool(BaseTool):
    name = "Generate Visualizations"
    description = "Creates different types of visualizations on the subset of data retrieved from the SQL query. Use this tool if the customer asks for a plot or visualization. Input should be a JSON string with keys 'user_question' and 'generated_sql'."

    def _run(self, input_str: str):
        input_dict = json.loads(input_str)
        return generate_visualizations(input_dict['user_question'], input_dict['generated_sql'])

class QuestionReformerTool(BaseTool):
    name = "Question Reformer"
    description = "Reformulates the user question to make it more understandable and answerable. Use this tool to reformulate the user question to make it more clear and concise, especially before using subset shap summary tool."

    def _run(self, user_question: str):
        return question_reformer(user_question)

class SubsetSHAPSummaryTool(BaseTool):
    name = "Subset SHAP Summary"
    description = "Calculates the SHAP summary of customers from the customer data query and SHAP feature contribution data for the same subset. Use this tool for understanding the main reasons for churn for a subset of customers. Input should be a JSON string with keys 'customer_data_sql_query', 'shap_data_sql_query', and 'user_question'."

    def _run(self, input_str: str):
        input_dict = json.loads(input_str)
        return subset_shap_summary(input_dict['customer_data_sql_query'], input_dict['shap_data_sql_query'], input_dict['user_question'])

class CustomerRecommendationsTool(BaseTool):
    name = "Customer Recommendations"
    description = "Generates recommendations to reduce churn probability for individual customers. Use this tool to generate customer recommendations for individual customers with high churn probability. Input should be a JSON string with keys 'user_question', 'customer_data_query', and 'counterfactual_data_query'."

    def _run(self, input_str: str):
        input_dict = json.loads(input_str)
        return customer_recommendations(input_dict['user_question'], input_dict['customer_data_query'], input_dict['counterfactual_data_query'])

# Initialize the tools
tools = [
    GenerateSQLTool(),
    ExecuteSQLTool(),
    SubsetChurnContributionAnalysisTool(),
    SubsetCLVAnalysisTool(),
    ModelStatTool(),
    GenerateVisualizationsTool(),
    QuestionReformerTool(),
    SubsetSHAPSummaryTool(),
    CustomerRecommendationsTool()
]


# Set custom instructions
custom_instructions = """You are a helpful AI assistant specialized in customer churn analysis. 
Your primary goal is to assist users with their queries about customer churn, using the tools at your disposal. 
Always strive to provide accurate and helpful information based on the data and tools available.

Here are some guidelines for using the tools:
1. Always use the Question Reformer tool first to make sure you understand the user's question correctly.
2. For questions requiring data retrieval, use the Generate SQL tool followed by the Execute SQL tool.
3. When using tools that require multiple inputs, format the input as a JSON string. For example:
   - Execute SQL: {"user_question": "...", "sql_generated": "...", "output_mode": "json"}
   - Subset Churn Contribution Analysis: {"user_question": "...", "sql_generated": "..."}
   - Generate Visualizations: {"user_question": "...", "generated_sql": "..."}
4. Use the Subset Churn Contribution Analysis tool to explain the impact of changes on churn for a subset of customers.
5. Use the Subset CLV Analysis tool to explain the impact of changes on Customer Lifetime Value.
6. Use the Model Stats tool when asked about model performance or accuracy.
7. Use the Generate Visualizations tool when the user asks for charts or visual representations of data.
8. Use the Subset SHAP Summary tool to understand the main reasons for churn in a subset of customers.
9. Use the Customer Recommendations tool to generate personalized recommendations for high-risk customers.
You have access to the following tools:

{tools}

Remember to chain tools together when necessary, and always provide clear explanations of your process and findings to the user."""

# Create the prompt
prompt = ChatPromptTemplate.from_messages([
    SystemMessage(content=custom_instructions),
    MessagesPlaceholder(variable_name="chat_history"),
    HumanMessage(content="{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad")
])

# Create the agent
agent = create_react_agent(llm, tools, prompt)

# Create the agent executor
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    memory=memory,
    verbose=True
)

# Example usage
while True:
    user_input = input("You: ")
    if user_input.lower() in ['exit', 'quit', 'bye']:
        break
    response = agent_executor.run(user_input)
    print(f"Agent: {response}")