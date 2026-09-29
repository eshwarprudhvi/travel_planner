from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from config.api_keys import GEMINI_API_KEY, GROQ_API_KEY



gemini_llm = ChatGoogleGenerativeAI(
    model="gemini-3.1-flash-lite",
    temperature=0,
    max_retries=3,
    api_key=GEMINI_API_KEY
)

groq_llm = ChatGroq(
    model="qwen/qwen3-32b",
    temperature=0.1,
    max_retries=3,
    api_key=GROQ_API_KEY
)

for chunk in gemini_llm.stream("Hello, how are you? write a 20 lines poem about the beauty of nature."):
    print(chunk.text, end="", flush=True)