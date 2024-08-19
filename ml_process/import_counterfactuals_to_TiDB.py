import os
import sys
from pathlib import Path
import yaml

# Load config file named conf.yml
with open('conf_telchurn.yml') as file:
    conf = yaml.load(file, Loader=yaml.FullLoader)

# Add the root directory to the Python path
root_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(root_dir))

# Import the CounterfactualRecommendationsImporter
from query_engine.insertsql import CounterfactualRecommendationsImporter

# Load the CounterfactualRecommendationsImporter
importer = CounterfactualRecommendationsImporter()

# Print the path of the CSV file for verification
csv_file_path = conf['dice']['cf_recommendations']
print(f"CSV file path from configuration: {csv_file_path}")

# Check if the file exists
if os.path.exists(csv_file_path):
    print(f"CSV file exists at the specified path.")
else:
    print(f"Error: CSV file does not exist at the specified path.")

# Import the data
##This won't import data to TiDB..We will upload it manually
## But counterfactual table have long text as one column and csv importer by default won't create table with longtext..So run this function to create the table
## And when copied to sql database use the created counterfactula table name
importer.create_table()
#importer.import_data(csv_file_path)