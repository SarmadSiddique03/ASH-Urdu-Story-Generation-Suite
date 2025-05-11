# rag_story_router.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import pandas as pd
import numpy as np
import ast
from dotenv import load_dotenv
import os
from sklearn.metrics.pairwise import cosine_similarity
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

# Setup
load_dotenv()

os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")

router = APIRouter()

# Pydantic input schema
class QueryRequest(BaseModel):
    query: str

# Load embedded data and embedder only once
EMBEDDED_CSV = "Data/embedded_prompts.csv"
df = pd.read_csv(EMBEDDED_CSV)
df['prompt_embeddings'] = df['prompt_embeddings'].apply(ast.literal_eval)
embedder = HuggingFaceEmbeddings(model_name="BAAI/bge-small-en-v1.5")

# LLM setup
llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.9)

# Prompt template
prompt_template = PromptTemplate(
    template="""
مندرجہ ذیل صارف کی درخواست کے مطابق اردو زبان میں ایک مکمل، دلچسپ اور اخلاقی کہانی تخلیق کریں۔

ہدایات:
- کہانی اردو زبان میں ہونی چاہیے، اور زبان میں روانی، فصاحت و بلاغت ہو۔
- سیاق و سباق میں دی گئی کہانی کو اندازِ بیان، اندازِ تحریر اور کہانی کے بہاؤ کے لحاظ سے بطور نمونہ استعمال کریں۔
- اگر سیاق و سباق دستیاب نہ ہو تو بھی صارف کی درخواست کے مطابق کہانی لازمی طور پر تخلیق کریں، اور کہانی صرف اردو زبان میں ہونی چاہیے۔
- اگر صارف کی درخواست (query) انگریزی یا رومن اردو میں ہو تو سب سے پہلے اس کو مہذب اور معیاری اردو میں ترجمہ کریں، پھر اسی ترجمہ شدہ اردو درخواست کے مطابق کہانی تخلیق کریں۔
- کہانی ہر حال میں اخلاقی اقدار کے مطابق ہونی چاہیے؛ کسی قسم کی فحش، غیر اخلاقی یا غیر مہذب زبان کا استعمال سختی سے منع ہے۔
- اگر صارف کی درخواست میں کوئی غیر اخلاقی، فحش یا غیر مہذب مواد موجود ہو تو کہانی تخلیق کرنے کے بجائے شائستگی سے یہ جواب دیا جائے:
  "آپ کی دی گئی درخواست غیر اخلاقی ہے۔ براہ کرم کوئی نیا اور موزوں موضوع فراہم کریں۔"
- کہانی میں کسی قسم کے تعارفی جملے شامل نہ ہوں۔
- کہانی کا ایک خوبصورت اور موزوں عنوان ضرور ہو، جو سب سے پہلے دیا جائے، اس کے فوراً بعد مکمل کہانی تحریر کی جائے۔
- اسی طرز کو برقرار رکھتے ہوئے صارف کی دی گئی درخواست کے مطابق نئی کہانی بنائیں۔

صارف کی درخواست:
{query}

انداز و اسلوب کی مثال (سیاق و سباق):
{context}
""",
    input_variables=["query", "context"]
)


def find_best_story_context(query: str):
    query_embedding = embedder.embed_query(query)
    similarities = cosine_similarity([query_embedding], df['prompt_embeddings'].tolist())[0]
    top_index = np.argmax(similarities)
    return df.iloc[top_index]['Story']



@router.post("/chat")
async def generate_story(data: QueryRequest):
    try:
        context_story = find_best_story_context(data.query)
        formatted_prompt = prompt_template.format(query=data.query, context=context_story)
        response = llm.invoke(formatted_prompt)

        return response.content
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating story: {str(e)}")
