import os
import sys

from dotenv import load_dotenv

# Add the project root to the Python path to allow imports from 'app'
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from app.flexline.client import FlexlineClient, FlexlineError

# Load environment variables from .env file
load_dotenv()


def run_flexline_test():
    """
    Initializes and tests the FlexlineClient by executing a SQL query
    loaded from the 'test_query.sql' file.
    """
    print("--- Starting Flexline Client Test ---")

    # 1. Load configuration from environment variables
    try:
        aws_key = os.environ["FLEXLINE_AWS_ACCESS_KEY_ID"]
        aws_secret = os.environ["FLEXLINE_AWS_SECRET_ACCESS_KEY"]
        api_key = os.environ["FLEXLINE_API_KEY"]
        username = os.environ["FLEXLINE_USERNAME"]
        password = os.environ["FLEXLINE_PASSWORD"]
    except KeyError as e:
        print(f"🚨 Configuration Error: Missing required environment variable {e}.")
        print(
            "Please ensure it is defined in your .env file with the 'FLEXLINE_' prefix."
        )
        return

    # 2. Load the SQL query from the dedicated file
    try:
        with open("test_query.sql", "r") as f:
            sql_query = f.read()
        print(f"Loaded query from test_query.sql:\n---{sql_query.strip()}\n---")
    except FileNotFoundError:
        print(
            "🚨 Error: `test_query.sql` not found. Please create this file in the root directory."
        )
        return

    # 3. Initialize the client
    print("Initializing Flexline client...")
    client = FlexlineClient(
        aws_access_key_id=aws_key,
        aws_secret_access_key=aws_secret,
        api_key=api_key,
        username=username,
        password=password,
    )

    # 4. Run the query execution process
    print("\nExecuting query...")
    try:
        results = client.run(sql_query)
        print("\n✅--- Lambda Execution Successful! ---✅")
        print("Received results:")
        import pandas as pd

        df = pd.DataFrame(results)
        print(df)
        print("\n--- Test Finished ---")
    except FlexlineError as e:
        print(f"\n🚨 Lambda Execution Failed: {e}")
    except Exception as e:
        print(f"\n🚨 An unexpected error occurred: {e}")


if __name__ == "__main__":
    run_flexline_test()
