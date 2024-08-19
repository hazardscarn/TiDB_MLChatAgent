import os
import csv
import json
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus

class CounterfactualRecommendationsImporter:
    def __init__(self):
        self.load_env_variables()
        self.engine = self.create_sqlalchemy_engine()

    def load_env_variables(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        dotenv_path = os.path.join(script_dir, '..', '.env')
        load_dotenv(dotenv_path)

        self.tidb_host = os.getenv('TIDB_HOST')
        self.tidb_port = int(os.getenv('TIDB_PORT', 4000))
        self.tidb_user = os.getenv('TIDB_USER')
        self.tidb_password = os.getenv('TIDB_PASSWORD')
        self.tidb_database = os.getenv('TIDB_DATABASE')
        self.tidb_ca_path = os.getenv('TIDB_CA_PATH')

    def create_sqlalchemy_engine(self):
        connection_string = (
            f"mysql+pymysql://{self.tidb_user}:{quote_plus(self.tidb_password)}@"
            f"{self.tidb_host}:{self.tidb_port}/{self.tidb_database}?"
        )

        if self.tidb_ca_path:
            connection_string += f"ssl_ca={quote_plus(self.tidb_ca_path)}&"

        connection_string += "ssl_verify_cert=true&ssl_verify_identity=true"

        return create_engine(connection_string)

    def create_table(self):
        with self.engine.connect() as connection:
            connection.execute(text("""
            CREATE TABLE IF NOT EXISTS counterfactual_recommendations (
                customerid INT PRIMARY KEY,
                changes LONGTEXT
            )
            """))

    def insert_data(self, customerid, changes):
        with self.engine.connect() as connection:
            sql = text("INSERT INTO counterfactual_recommendations (customerid, changes) VALUES (:customerid, :changes) ON DUPLICATE KEY UPDATE changes = VALUES(changes)")
            connection.execute(sql, {"customerid": customerid, "changes": json.dumps(changes)})

    def import_data(self, csv_file_path):
        self.create_table()

        try:
            print(f"Attempting to open file: {csv_file_path}")
            with open(csv_file_path, 'r') as file:
                csv_reader = csv.DictReader(file)
                row_count = 0
                for row in csv_reader:
                    row_count += 1
                    customerid = int(row['customerid'])
                    try:
                        changes = json.loads(row['changes'].replace("'", '"'))
                        self.insert_data(customerid, changes)
                        print(f"Inserted data for customer ID {customerid}")
                    except json.JSONDecodeError as json_error:
                        print(f"Error parsing JSON for customer ID {customerid}: {json_error}")
                        print(f"Problematic JSON string: {row['changes']}")
                    except Exception as insert_error:
                        print(f"Error inserting data for customer ID {customerid}: {insert_error}")

            print(f"Processed {row_count} rows from the CSV file.")
            print("Data import completed.")
        except FileNotFoundError:
            print(f"Error: CSV file not found at {csv_file_path}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

