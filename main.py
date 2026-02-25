from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse
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
3. Take food orders
4. Ask for customer NAME and PHONE NUMBER before confirming order
5. Confirm order with total price in Pakistani Rupees
6. When order is complete with name and phone, end your message with this exact format on a new line:
   ORDER_COMPLETE:{"name":"customer name","phone":"phone number","items":["item1","item2"],"total":1234}

Rules:
- Be friendly and use Pakistani expressions like "Zaroor!", "Bilkul!", "Shukriya!"
- If someone writes in Urdu, reply in Urdu. If in English, reply in English.
- Always collect name and phone before finalizing order
- Only add ORDER_COMPLETE line when you have name, phone, and confirmed items"""

class Message(BaseModel):
    text: str
    session_id: str = "default"

@app.get("/")
def home():
    return {"message": "AI Call Center is running!"}

@app.post("/chat")
def chat(message: Message):
    if message.session_id not in conversations:
        conversations[message.session_id] = []
    
    history = conversations[message.session_id]
    history.append({"role": "user", "content": message.text})
    
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
    history.append({"role": "assistant", "content": bot_reply})
    
    if len(history) > 20:
        conversations[message.session_id] = history[-20:]
    
    # Detect completed order
    if "ORDER_COMPLETE:" in bot_reply:
        try:
            import json, re
            match = re.search(r'ORDER_COMPLETE:(\{.*\})', bot_reply)
            if match:
                order_data = json.loads(match.group(1))
                order_data["id"] = len(orders) + 1
                order_data["time"] = __import__('datetime').datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                orders.append(order_data)
                bot_reply = bot_reply.replace(match.group(0), "").strip()
        except:
            pass
    
    return {"response": bot_reply}

@app.get("/orders")
def get_orders():
    return {"total_orders": len(orders), "orders": orders}
@app.get("/app")
def serve_frontend():
    return FileResponse("index.html")

@app.get("/admin")
def admin_dashboard():
    html = """
<!DOCTYPE html>
<html>
<head>
    <title>Admin Dashboard</title>
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="30">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', sans-serif; background: #f0f2f5; padding: 20px; }
        .header { background: linear-gradient(135deg, #25D366, #128C7E); color: white; padding: 25px; border-radius: 15px; margin-bottom: 25px; }
        .header h1 { font-size: 24px; }
        .header p { opacity: 0.85; margin-top: 5px; }
        .stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin-bottom: 25px; }
        .stat-card { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.08); text-align: center; }
        .stat-card h2 { font-size: 32px; color: #25D366; }
        .stat-card p { color: #666; margin-top: 5px; }
        .orders-table { background: white; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.08); overflow: hidden; }
        .orders-table h3 { padding: 20px; border-bottom: 1px solid #eee; color: #333; }
        table { width: 100%; border-collapse: collapse; }
        th { background: #f8f9fa; padding: 12px 20px; text-align: left; color: #666; font-size: 13px; }
        td { padding: 15px 20px; border-bottom: 1px solid #f0f0f0; }
        tr:last-child td { border-bottom: none; }
        .badge { background: #e8f5e9; color: #25D366; padding: 4px 10px; border-radius: 20px; font-size: 12px; font-weight: bold; }
        .no-orders { text-align: center; padding: 40px; color: #999; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🍽️ AI Restaurant — Admin Dashboard</h1>
        <p>Live orders • Auto-refreshes every 30 seconds</p>
    </div>
    <div class="stats">
        <div class="stat-card">
            <h2>""" + str(len(orders)) + """</h2>
            <p>Total Orders</p>
        </div>
        <div class="stat-card">
            <h2>Rs.""" + str(sum(o.get('total', 0) for o in orders)) + """</h2>
            <p>Total Revenue</p>
        </div>
        <div class="stat-card">
            <h2>""" + str(len(set(o.get('phone','') for o in orders))) + """</h2>
            <p>Unique Customers</p>
        </div>
    </div>
    <div class="orders-table">
        <h3>📋 All Orders</h3>
        """ + ("""
        <table>
            <tr>
                <th>#</th>
                <th>Customer</th>
                <th>Phone</th>
                <th>Items</th>
                <th>Total</th>
                <th>Time</th>
            </tr>
            """ + "".join([f"""
            <tr>
                <td>{o.get('id','')}</td>
                <td><b>{o.get('name','')}</b></td>
                <td>{o.get('phone','')}</td>
                <td>{', '.join(o.get('items', []))}</td>
                <td><span class="badge">Rs.{o.get('total','')}</span></td>
                <td>{o.get('time','')}</td>
            </tr>
            """ for o in reversed(orders)]) + """
        </table>
        """ if orders else '<div class="no-orders">No orders yet. Start chatting! 🤖</div>') + """
    </div>
</body>
</html>
"""
    return HTMLResponse(content=html)