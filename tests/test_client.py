import os
import sys

from dotenv import load_dotenv

# We need to adjust the path to import from the app directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.text2sql.client import Text2SQLClient

# Load environment variables from .env file
load_dotenv()


def run_test(question: str):
    """
    Initializes and tests the Text2SQLClient, enforcing that all
    required configuration variables are present.
    """
    print("--- Starting Text-to-SQL Client Test ---")

    # 1. Load configuration from environment variables with strict checking
    try:
        base_url = os.environ["SaaS_API_BASE_URL"]
        username = os.environ["SaaS_API_USERNAME"]
        password = os.environ["SaaS_API_PASSWORD"]
        workspace_id = os.environ["WORKSPACE_ID"]
    except KeyError as e:
        print(f"🚨 Configuration Error: Missing required environment variable {e}.")
        print("Please ensure it is defined in your .env file.")
        return

    # 2. Initialize the client
    print(f"Initializing client for workspace: {workspace_id}")
    client = Text2SQLClient(base_url=base_url, workspace_id=workspace_id)

    # 3. Authenticate
    print("Authenticating with the SaaS API...")
    if not client.authenticate(username, password):
        print("Authentication failed. Please check credentials or API status.")
        return
    print("✅ Authentication successful!")

    # 4. Get SQL query
    print(f"\nRequesting SQL for the question: '{question.strip()}'")
    ai_response = client.get_sql(question)

    if ai_response:
        print("✅ Successfully received AI response.")
        is_read_only = ai_response.get("read_only", False)
        print(f"Read-Only Flag: {is_read_only}")

        if not is_read_only:
            print(
                "\n🚨 TEST FAILED: The client should have rejected this query, but it was processed."
            )
            return

        sql_query = ai_response.get("sql_query")
        explanation = ai_response.get("explanation")

        print("\n--- SQL Query ---")
        print(sql_query)
        print("\n--- Explanation ---")
        print(explanation)
        print("\n--- Test Finished ---")
    else:
        print(
            "✅ Test Passed: The request was correctly rejected by the client (e.g., not read-only) or failed for other reasons."
        )


if __name__ == "__main__":
    # Check if a question was provided as a command-line argument
    if len(sys.argv) > 1:
        # Use the question from the command line
        user_question = " ".join(sys.argv[1:])
        print("Using question from command-line argument.")
    else:
        # Otherwise, read the default question from a file
        print("No command-line argument given, reading from 'tests/test_question.txt'.")
        try:
            with open("tests/test_question.txt", "r") as f:
                user_question = f.read().strip()
        except FileNotFoundError:
            print(
                "🚨 Error: 'tests/test_question.txt' not found. Please create it or provide a question as an argument."
            )
            sys.exit(1)  # Exit the script if the file is not found

    run_test(user_question)
