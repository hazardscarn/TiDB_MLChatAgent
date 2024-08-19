from abc import ABC
# import vertexai
# from vertexai.language_models import TextGenerationModel
# from vertexai.language_models import CodeGenerationModel
# from vertexai.language_models import CodeChatModel
# from vertexai.generative_models import GenerativeModel
# from vertexai.generative_models import HarmCategory,HarmBlockThreshold
# from vertexai.generative_models import GenerationConfig
# from vertexai.language_models import TextEmbeddingModel
import time
import json
import pandas as pd
from datetime import datetime
import google.auth
import pandas as pd
import yaml
from google.cloud.exceptions import NotFound
from google.generativeai import configure
import os
from langchain_google_genai import GoogleGenerativeAI, GoogleGenerativeAIEmbeddings

# configure(api_key=os.getenv('GOOGLE_API_KEY'))

with open('./llm_configs.yml') as file:
    conf = yaml.load(file, Loader=yaml.FullLoader)


class Agent(ABC):
    """
    The core class for all Agents
    """

    agentType: str = "Agent"

    def __init__(self, model_id: str, api_key: str):
        self.model_id = model_id
        self.api_key = api_key
        # print(f"Initializing Agent with API key: {api_key}")
        self.model = GoogleGenerativeAI(model=model_id, google_api_key=api_key)

class QueryRefiller(Agent, ABC):
    agentType: str = "QueryFillerAgent"

    def __init__(self, model_id: str, api_key: str):
        super().__init__(model_id, api_key)
        # print(f"Initializing QueryRefiller with API key: {api_key}")

    def check(self, generated_sql):

        context_prompt = conf['query_filler']['prompt']+f"""
        
        Here is the SQL generated:
        {generated_sql}

        Output: reframed_query

        Note:
        - Output only the reframed query.
        - Do not add any extra text, SQL keywords, or symbols (e.g., "sql", "```", "output").
        """

        reformed_sql = self.model.invoke(context_prompt)
        return reformed_sql
    

##Embedding Agent is used to embed Known Good SQL,Table summarries and embed user question to retrive answers
class EmbedderAgent(Agent, ABC): 
    """ 
    This Agent generates embeddings 
    """ 

    agentType: str = "EmbedderAgent"

    def __init__(self, mode, embeddings_model='models/embedding-001'):
            super().__init__(model_id=embeddings_model)
            self.mode = mode
            self.model = GoogleGenerativeAIEmbeddings(model=embeddings_model)



    def create(self, question):
        if isinstance(question, str):
            return self.model.embed_query(question)
        elif isinstance(question, list):
            return self.model.embed_documents(question)
        else:
            raise ValueError('Input must be either str or list')



