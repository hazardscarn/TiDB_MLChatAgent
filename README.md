# TiDB_MLChatAgent

Effortlessly chat with your ML model using TiDB Serverless and Gemini Models to get the best insights.

## Features

- Natural language interaction with ML models
- Powered by TiDB Serverless for efficient data management
- Utilizes Gemini Models for advanced language processing
- Supports churn analysis, customer service assistance, and more

## Prerequisites

- Python 3.11+
- TiDB Serverless account
- Google Cloud account (for Gemini API access)

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/hazardscarn/TiDB_MLChatAgent.git
   cd TiDB_MLChatAgent
   ```

2. Install required packages:
   ```
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   Create a `.env` file in the root directory with the following contents:

   ```
   GOOGLE_API_KEY="your_google_api_key"
   TIDB_HOST="your_tidb_host"
   TIDB_PORT=your_port_number
   TIDB_USER="your_tidb_username"
   TIDB_PASSWORD="your_tidb_password"
   TIDB_DATABASE="your_database_name"
   TIDB_DATA_APP_PUBLIC_KEY="your_public_key"
   DATA_APP_PRIVATE_KEY="your_private_key"
   CHAT2QUERY_API_KEY="your_chat2query_api_key"
   DATA_APP_BASE_URL="your_data_app_base_url"
   TIDB_CLUSTER_ID="your_cluster_id"
   TIDB_APP_ID="your_app_id"
   ```

   Replace the placeholder values with your actual credentials.

## Usage

1. Build the model:
   Run the scripts in the `ml_process` directory sequentially to create the model object.

2. Import data to TiDB:
   Move your customer data, SHAP data, and counterfactual data to TiDB Serverless.

3. Run the application:
   ```
   streamlit run mlchatbot.py
   ```

4. Access the web interface through your browser and start chatting with your ML model!

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

For any suggestions, queries, or support needs, please contact:
David

Email: davidacad10@gmail.com
LinkedIn: https://www.linkedin.com/in/david-babu-15047096/

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

```
Copyright 2024 David

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
```