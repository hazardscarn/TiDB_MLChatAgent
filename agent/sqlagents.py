from abc import ABC
import vertexai
from vertexai.language_models import TextGenerationModel
from vertexai.language_models import CodeGenerationModel
from vertexai.language_models import CodeChatModel
from vertexai.generative_models import GenerativeModel
from vertexai.generative_models import HarmCategory,HarmBlockThreshold
from vertexai.generative_models import GenerationConfig
from vertexai.language_models import TextEmbeddingModel
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

configure(api_key=os.getenv('GOOGLE_API_KEY'))

with open('./llm_configs.yml') as file:
    conf = yaml.load(file, Loader=yaml.FullLoader)


class Agent(ABC):
    """
    The core class for all Agents
    """

    agentType: str = "Agent"

    def __init__(self,
                model_id:str):
        """
        Args:
            PROJECT_ID (str | None): GCP Project Id.
            dataset_name (str): 
            TODO
        """

        self.model_id = model_id 

        if model_id == 'code-bison-32k':
            self.model = CodeGenerationModel.from_pretrained('code-bison-32k')
        elif model_id == 'text-bison-32k':
            self.model = TextGenerationModel.from_pretrained('text-bison-32k')
        elif model_id == 'gemini-1.0-pro':
            self.model = GenerativeModel("gemini-1.0-pro")
        elif model_id == 'gemini-1.5-flash-001':
            self.model = GenerativeModel("gemini-1.5-flash-001")
        else:
            raise ValueError("Please specify a compatible model.")

class QueryRefiller(Agent, ABC): 
    """ 
    This Agent makes sure the query uses select * and not subset of columns for specific processes
    """ 

    agentType: str = "QueryFillerAgent"


    def check(self, generated_sql):

        context_prompt = conf['query_filler']['prompt']+f"""
        
        Here is the SQL generated:
        {generated_sql}

        Output: reframed_query

        Note:
        - Output only the reframed query.
        - Do not add any extra text, SQL keywords, or symbols (e.g., "sql", "```", "output").
        """


        if self.model_id =='gemini-1.5-flash-001' or self.model_id == 'gemini-1.0-pro':
            context_query = self.model.generate_content(context_prompt, stream=False)
            reformed_sql = str(context_query.candidates[0].text)

        else:
            context_query = self.model.predict(context_prompt, max_output_tokens = 8000, temperature=0)
            reformed_sql = str(context_query.candidates[0])

        return reformed_sql
    

##Embedding Agent is used to embed Known Good SQL,Table summarries and embed user question to retrive answers
class EmbedderAgent(Agent, ABC): 
    """ 
    This Agent generates embeddings 
    """ 

    agentType: str = "EmbedderAgent"

    def __init__(self, mode, embeddings_model='textembedding-gecko@002'): 
        if mode == 'vertex': 
            self.mode = mode 
            self.model = TextEmbeddingModel.from_pretrained(embeddings_model)

        else: raise ValueError('EmbedderAgent mode must be vertex')



    def create(self, question): 
        """Text embedding with a Large Language Model."""

        if self.mode == 'vertex': 
            if isinstance(question, str): 
                embeddings = self.model.get_embeddings([question])
                for embedding in embeddings:
                    vector = embedding.values
                return vector
            
            elif isinstance(question, list):  
                vector = list() 
                for q in question: 
                    embeddings = self.model.get_embeddings([q])

                    for embedding in embeddings:
                        vector.append(embedding.values) 
                return vector
            
            else: raise ValueError('Input must be either str or list')

