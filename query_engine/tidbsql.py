import os
import time
import json
from dotenv import load_dotenv
import requests
from requests.auth import HTTPDigestAuth
import pandas as pd
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus

class TiDBChat2SQL:
    def __init__(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        dotenv_path = os.path.join(script_dir, '..', '.env')
        load_dotenv(dotenv_path)

        self.region = "us-east-1"
        self.app_id = os.getenv('TIDB_APP_ID')
        self.public_key = os.getenv('TIDB_DATA_APP_PUBLIC_KEY')
        self.private_key = os.getenv('DATA_APP_PRIVATE_KEY')
        self.cluster_id = os.getenv('TIDB_CLUSTER_ID')
        self.database = os.getenv('TIDB_DATABASE')
        
        self.base_url = f"https://{self.region}.data.tidbcloud.com/api/v1beta/app/{self.app_id}/endpoint"
        self.summary_url = f"{self.base_url}/v3/dataSummaries"
        self.job_status_url = f"{self.base_url}/v2/jobs"
        self.chat2data_url = f"{self.base_url}/v3/chat2data"
        self.refine_sql_url = f"{self.base_url}/v3/refineSql"
        
        self.data_summary_job_id = self.load_data_summary_job_id()

        # TiDB connection details
        self.tidb_host = os.getenv('TIDB_HOST')
        self.tidb_port = int(os.getenv('TIDB_PORT', 4000))
        self.tidb_user = os.getenv('TIDB_USER')
        self.tidb_password = os.getenv('TIDB_PASSWORD')
        self.tidb_ca_path = os.getenv('TIDB_CA_PATH')

        self.engine = self.create_sqlalchemy_engine()

    def create_sqlalchemy_engine(self):
        connection_string = (
            f"mysql+pymysql://{self.tidb_user}:{quote_plus(self.tidb_password)}@"
            f"{self.tidb_host}:{self.tidb_port}/{self.database}?"
        )
        
        if self.tidb_ca_path:
            connection_string += f"ssl_ca={quote_plus(self.tidb_ca_path)}&"
        
        connection_string += "ssl_verify_cert=true&ssl_verify_identity=true"
        
        return create_engine(connection_string)

    def load_data_summary_job_id(self):
        config_file = os.path.join(os.path.dirname(__file__), 'data_summary_config.json')
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                config = json.load(f)
                return config.get('data_summary_job_id')
        return None

    def save_data_summary_job_id(self, job_id):
        config_file = os.path.join(os.path.dirname(__file__), 'data_summary_config.json')
        with open(config_file, 'w') as f:
            json.dump({'data_summary_job_id': job_id}, f)

    def api_request(self, url, method='GET', data=None):
        headers = {'Content-Type': 'application/json'}
        try:
            if method == 'GET':
                response = requests.get(url, auth=HTTPDigestAuth(self.public_key, self.private_key), headers=headers)
            elif method == 'POST':
                response = requests.post(url, auth=HTTPDigestAuth(self.public_key, self.private_key), headers=headers, json=data)
            
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"API request error: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Error response: {e.response.text}")
            return None

    def generate_data_summary(self, force=False):
        if self.data_summary_job_id and not force:
            print("Using existing data summary.")
            return self.data_summary_job_id

        print("Initiating data summary generation...")
        data = {
            "cluster_id": self.cluster_id,
            "database": self.database,
            "description": f"Data summary for {self.database}",
            "reuse": False
        }
        response = self.api_request(self.summary_url, method='POST', data=data)
        if response and 'result' in response:
            self.data_summary_job_id = response['result']['job_id']
            self.save_data_summary_job_id(self.data_summary_job_id)
            print(f"Data summary generation job initiated. Job ID: {self.data_summary_job_id}")
            self.wait_for_job_completion(self.data_summary_job_id)
            return self.data_summary_job_id
        print("Failed to initiate data summary generation.")
        return None

    def wait_for_job_completion(self, job_id):
        while True:
            status, _ = self.check_job_status(job_id)
            if status == 'done':
                print("Job completed successfully.")
                break
            elif status == 'failed':
                print("Job failed.")
                return
            else:
                print("Job is still in progress. Waiting...")
                time.sleep(10)

    def chat2sql(self, question, max_retries=5, timeout=60):
        if not self.data_summary_job_id:
            print("No data summary found. Generating one...")
            self.generate_data_summary()

        for attempt in range(max_retries):
            print(f"Generating SQL (Attempt {attempt + 1}/{max_retries})...")
            query_job_id = self.initiate_sql_generation(question)
            if not query_job_id:
                print("Failed to initiate SQL generation.")
                continue

            generated_sql = self.get_generated_sql(query_job_id, timeout)
            if not generated_sql:
                print("Failed to generate SQL.")
                continue

            print("\nGenerated SQL:", generated_sql)
            
            if self.check_query(generated_sql):
                return generated_sql
            
            print("SQL check failed. Attempting to refine...")
            refined_sql = self.refine_sql(generated_sql, "The previous SQL failed to execute. Please refine it.")
            if refined_sql and self.check_query(refined_sql):
                print("\nRefined SQL:", refined_sql)
                return refined_sql

        print(f"Failed to generate valid SQL after {max_retries} attempts.")
        return None

    def initiate_sql_generation(self, question):
        data = {
            "cluster_id": self.cluster_id,
            "database": self.database,
            "question": question,
            "sql_generate_mode": "direct"
        }
        response = self.api_request(self.chat2data_url, method='POST', data=data)
        if response and 'result' in response:
            return response['result'].get('job_id')
        print(f"Failed to initiate SQL generation. Response: {response}")
        return None

    def get_generated_sql(self, job_id, timeout=60):
        start_time = time.time()
        while time.time() - start_time < timeout:
            status, result = self.check_job_status(job_id)
            print(f"Job status: {status}")
            if status == 'done':
                return result.get('sql')
            elif status == 'failed':
                print(f"SQL generation failed. Result: {result}")
                return None
            time.sleep(2)
        print(f"SQL generation timed out after {timeout} seconds.")
        return None

    def check_job_status(self, job_id):
        response = self.api_request(f"{self.job_status_url}/{job_id}")
        if response and 'result' in response:
            return response['result']['status'], response['result'].get('result')
        print(f"Failed to check job status. Response: {response}")
        return None, None

    def api_request(self, url, method='GET', data=None):
        headers = {'Content-Type': 'application/json'}
        try:
            if method == 'GET':
                response = requests.get(url, auth=HTTPDigestAuth(self.public_key, self.private_key), headers=headers)
            elif method == 'POST':
                response = requests.post(url, auth=HTTPDigestAuth(self.public_key, self.private_key), headers=headers, json=data)
            
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"API request error: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Error response: {e.response.text}")
            return None

    def refine_sql(self, sql, instruction):
        data = {
            "cluster_id": self.cluster_id,
            "database": self.database,
            "sql": sql,
            "instruction": instruction
        }
        response = self.api_request(self.refine_sql_url, method='POST', data=data)
        if response and 'result' in response:
            return response['result'].get('sql')
        return None

    def check_query(self, sql):
        try:
            with self.engine.connect() as connection:
                connection.execute(text("EXPLAIN " + sql))
            return True
        except Exception as e:
            print(f"Query check failed: {e}")
            return False

    def execute_sql(self, sql):
        real_engine = self.engine.engine if hasattr(self.engine, 'engine') else self.engine

        try:
            start_time = time.time()
            with real_engine.connect() as connection:
                result = connection.execute(text(sql))
                df = pd.DataFrame(result.fetchall(), columns=result.keys())
            end_time = time.time()
            print(f"SQL execution time: {end_time - start_time:.4f} seconds")
            return df
        except Exception as e:
            print(f"Error executing SQL: {e}")
            return None