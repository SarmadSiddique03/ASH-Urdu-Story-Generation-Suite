
# history_chatbot_api.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from langchain.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.memory import ConversationBufferMemory
from duckduckgo_search import DDGS
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import requests
import random
import time
import os

# Load environment variables (though main.py also does this, it's good practice here too)
load_dotenv()

router = APIRouter()

# --- LangChain Setup ---
# Memory is managed by the caller (main.py) and passed in the request
memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True) # REMOVED

# Initialize LLM
# Ensure GOOGLE_API_KEY is set in your environment or .env file
try:
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.7)
    # memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

except Exception as e:
    print(f"Error initializing Google Generative AI model: {e}")
    # You might want to raise an exception or handle this more gracefully
    # depending on your application's startup requirements.

# Define the prompt template (same as before)
prompt_template = PromptTemplate(
    input_variables=["question", "context", "websearch", "chat_history"],
    template="""
آپ ایک ماہر اردو محقق، مؤرخ، اور علمی مصنف ہیں۔ آپ کا مقصد یہ ہے کہ صارف کے سوال کا تفصیلی، مستند اور مدلل جواب اردو زبان میں فراہم کریں۔

سب سے پہلے سوال کا تجزیہ کریں:
- اگر سوال اردو تاریخ یا اردو زبان کی تاریخ سے متعلق ہے تو آگے بڑھ کر مکمل جواب دیں۔
- اگر سوال اردو تاریخ یا اردو زبان کی تاریخ سے متعلق نہیں ہے تو مہذب انداز میں جواب دیں کہ براہ کرم اردو تاریخ یا اردو زبان کی تاریخ سے متعلق سوال پوچھیں۔

مندرجہ ذیل معلومات کا بغور مطالعہ کریں اور ان کی روشنی میں جامع اور واضح جواب فراہم کریں (اگر سوال متعلقہ ہو):

سیاق و سباق (Context):
{context}

ویب تلاش کے نتائج (Web Search Results):
{websearch}

گفتگو کی سابقہ تاریخ (Conversation History):
{chat_history}

**اگر گفتگو کی سابقہ تاریخ (chat_history) دستیاب ہے تو اس کا مطلب ہے کہ یہ جاری گفتگو کا حصہ ہے۔ ایسے میں سوالات کا تعلق سابقہ گفتگو میں زیر بحث آنے والے افراد یا چیزوں سے ہو سکتا ہے۔ براہ کرم سابقہ گفتگو کو مدنظر رکھتے ہوئے جواب فراہم کریں۔**

اب صارف کے سوال کا تجزیہ کریں اور مناسب ردعمل دیں:

سوال: {question}

جواب (صرف اردو میں دیں):
"""
)


# --- Web Search Helper Functions (same as before) ---
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Mozilla/5.0 (X11; Linux x86_64)",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)",
]

def search_web(query, top_k=3):
    results = []
    try:
        # Use max_results parameter as before
        with DDGS() as ddgs:
             for r in ddgs.text(query, max_results=top_k):
                headers = {"User-Agent": random.choice(USER_AGENTS)}
                # Pass headers to extraction function
                snippet = extract_text_from_url(r["href"], headers=headers)
                results.append(snippet)
                # Add sleep to be polite to websites and avoid rate limits
                time.sleep(random.uniform(1.2, 2.5))
    except Exception as e:
        results.append(f"❌ Web search failed: {e}")
    return "\n\n".join(results)

def extract_text_from_url(url, headers):
    try:
        # Use headers in the request
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status() # Raise an exception for bad status codes
        soup = BeautifulSoup(res.text, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose() # Remove script, style, noscript tags
        # Extract text from paragraph tags, stripping whitespace
        paragraphs = soup.find_all("p")
        if not paragraphs: # If no paragraphs found, try body text
             return soup.body.get_text(strip=True) if soup.body else "No readable text found."
        return "\n".join(p.get_text(strip=True) for p in paragraphs)
    except requests.exceptions.RequestException as e:
        return f"❌ Failed to retrieve/process {url}: {e}"
    except Exception as e:
        return f"❌ An unexpected error occurred extracting from {url}: {e}"


# --- Pydantic Model for Request Body ---
class HistoryChatRequest(BaseModel):
    question: str


# --- API Endpoint ---
@router.post("/chat", tags=["History Chatbot"])
async def handle_history_chat(request_data: HistoryChatRequest):
    """
    Handles a history chatbot query.
    Performs web search, formats prompt with provided history, and invokes the LLM.
    """
    try:
        current_chat_history = memory.load_memory_variables({})["chat_history"]
        context = ""
        websearch = search_web(request_data.question)

        prompt = prompt_template.format(
            question=request_data.question,
            context=context,
            websearch=websearch,
            chat_history=current_chat_history,
        )

        # Replace this with your actual model response logic
        response = llm.invoke(prompt)
        memory.save_context({"input": request_data.question}, {"output": response.content})
        return response.content

    except Exception as e:
        print(f"Error in history chatbot endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

