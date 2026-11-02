
import os
from dotenv import load_dotenv
from google import genai

# Load environment variables
load_dotenv()

# Read Gemini API key
API_KEY = os.getenv("GEMINI_API_KEY")

# Create Gemini client
client = genai.Client(api_key=API_KEY) if API_KEY else None


def get_ai_response(user_message, financial_context=""):
    if client is None:
        return "Gemini API key is missing. Please check your .env file."

    prompt = f"""
    You are FinTrack AI, a helpful personal finance assistant.

    Help users understand their spending, budgets and savings.

    Give simple, practical and easy-to-understand financial suggestions.

    Do not invent financial figures.
    Do not claim to be a certified financial advisor.

    Financial information:
    {financial_context}

    User question:
    {user_message}
    """

    try:
        response = client.models.generate_content(
         model="gemini-3.5-flash-lite",
         contents=prompt
        )

        return response.text or "Sorry, I could not generate a response."

    except Exception as error:
        print("Gemini API Error:", error)
        return "Sorry, the AI assistant is temporarily unavailable."
