import google.generativeai as genai

GEMINI_API_KEY = "AIzaSyArxRjHcU8sC-75I6UoD_6ng_DLY0kfqzU" 
genai.configure(api_key=GEMINI_API_KEY)

print("--- Available Models ---")
for m in genai.list_models():
    if 'generateContent' in m.supported_generation_methods:
        print(m.name)

print("\n--- Testing Gemini Pro ---")
try:
    model = genai.GenerativeModel('gemini-pro')
    response = model.generate_content("hello")
    print(f"Success with gemini-pro: {response.text[:20]}")
except Exception as e:
    print(f"Failed with gemini-pro: {e}")

print("\n--- Testing Gemini 1.5 Flash ---")
try:
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content("hello")
    print(f"Success with gemini-1.5-flash: {response.text[:20]}")
except Exception as e:
    print(f"Failed with gemini-1.5-flash: {e}")
