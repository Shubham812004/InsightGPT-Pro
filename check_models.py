import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

print("Attempting to configure API...")
try:
    # Configure the client library with your API key
    genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
    print("API configured successfully.")
except Exception as e:
    print(f"Failed to configure API: {e}")
    exit()

print("\nFetching available models...\n")

# List all available models and find the ones that support text generation
found_model = False
for model in genai.list_models():
    # Check if the model supports the 'generateContent' method
    if 'generateContent' in model.supported_generation_methods:
        print(f"Found usable model: {model.name}")
        found_model = True

if not found_model:
    print("\nCould not find any models that support text generation for your API key.")
    print("This might be a regional issue or a problem with your Google AI project setup.")