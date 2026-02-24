from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from groq import Groq
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Paste your Groq API key here
from dotenv import load_dotenv
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

client = Groq(api_key=GROQ_API_KEY)

# Store orders and conversation history
orders = []
conversations = {}

SYSTEM_PROMPT = """You are a friendly AI assistant for a Pakistani restaurant called "AI Restaurant".
You speak both Urdu and English naturally (the way Pakistanis mix both languages).

Our Menu:
- Zinger Burger: Rs.350
- Chicken Karahi: Rs.850
- Biryani: Rs.450
- Fries: Rs.150
- Cold Drink: Rs.100
- Pizza: Rs.700

Your job is to:
1. Greet customers warmly
2. Show menu when asked
3. Take food orders and confirm them with total price in Pakistani Rupees
4. Answer any questions about the food
5. Be friendly and use Pakistani expressions like "Zaroor!", "Bilkul!", "Shukriya!"

When a customer places an order, always:
- List the items they ordered
- Calculate and show the total in Rs.
- Confirm the order warmly

Keep responses concise and friendly. If someone writes in Urdu, reply in Urdu. If in English, reply in English."""

class Message(BaseModel):
    text: str
    session_id: str = "default"

@app.get("/")
def home():
    return {"message": "AI Call Center is running!"}

@app.post("/chat")
def chat(message: Message):
    # Get or create conversation history for this session
    if message.session_id not in conversations:
        conversations[message.session_id] = []
    
    history = conversations[message.session_id]
    
    # Add user message to history
    history.append({
        "role": "user",
        "content": message.text
    })
    
    # Call Groq AI
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            *history
        ],
        max_tokens=500,
        temperature=0.7
    )
    
    bot_reply = response.choices[0].message.content
    
    # Save bot reply to history
    history.append({
        "role": "assistant",
        "content": bot_reply
    })
    
    # Keep history manageable (last 20 messages)
    if len(history) > 20:
        conversations[message.session_id] = history[-20:]
    
    return {"response": bot_reply}

@app.get("/orders")
def get_orders():
    return {"total_orders": len(orders), "orders": orders}