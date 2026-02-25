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
    total_revenue = sum(o.get('total', 0) for o in orders)
    total_orders = len(orders)
    unique_customers = len(set(o.get('phone','') for o in orders))
    avg_rating = round(sum(o.get('rating', 0) for o in orders if o.get('rating')) / max(len([o for o in orders if o.get('rating')]), 1), 1)

    # Build chart data
    from collections import Counter
    item_counts = Counter()
    for o in orders:
        for item in o.get('items', []):
            item_counts[item] += 1
    top_items = item_counts.most_common(5)
    chart_labels = str([i[0] for i in top_items])
    chart_values = str([i[1] for i in top_items])

    html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Admin Dashboard</title>
    <meta charset="UTF-8">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Inter', sans-serif; background: #0f0f1a; color: #e2e8f0; padding: 24px; }}
        
        .header {{
            background: linear-gradient(135deg, #667eea, #764ba2);
            padding: 24px 28px;
            border-radius: 16px;
            margin-bottom: 24px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .header h1 {{ font-size: 22px; font-weight: 700; }}
        .header p {{ opacity: 0.85; font-size: 13px; margin-top: 4px; }}
        .live-badge {{
            background: rgba(255,255,255,0.2);
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 12px;
            display: flex;
            align-items: center;
            gap: 6px;
        }}
        .live-dot {{
            width: 7px; height: 7px;
            background: #22c55e;
            border-radius: 50%;
            animation: blink 2s infinite;
        }}
        @keyframes blink {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.3; }}
        }}

        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 16px;
            margin-bottom: 24px;
        }}
        .stat-card {{
            background: #1e1e32;
            border: 1px solid rgba(255,255,255,0.06);
            padding: 20px;
            border-radius: 14px;
        }}
        .stat-card .icon {{
            font-size: 24px;
            margin-bottom: 12px;
        }}
        .stat-card .value {{
            font-size: 28px;
            font-weight: 700;
            color: #a78bfa;
        }}
        .stat-card .label {{
            font-size: 13px;
            color: #64748b;
            margin-top: 4px;
        }}

        .charts-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 16px;
            margin-bottom: 24px;
        }}
        .chart-card {{
            background: #1e1e32;
            border: 1px solid rgba(255,255,255,0.06);
            padding: 20px;
            border-radius: 14px;
        }}
        .chart-card h3 {{
            font-size: 14px;
            font-weight: 600;
            margin-bottom: 16px;
            color: #94a3b8;
        }}

        .orders-card {{
            background: #1e1e32;
            border: 1px solid rgba(255,255,255,0.06);
            border-radius: 14px;
            overflow: hidden;
        }}
        .orders-card-header {{
            padding: 20px 24px;
            border-bottom: 1px solid rgba(255,255,255,0.06);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .orders-card-header h3 {{ font-size: 15px; font-weight: 600; }}
        .orders-count {{
            background: rgba(167,139,250,0.15);
            color: #a78bfa;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
        }}

        table {{ width: 100%; border-collapse: collapse; }}
        th {{
            padding: 12px 24px;
            text-align: left;
            font-size: 12px;
            color: #475569;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            background: #16162a;
        }}
        td {{
            padding: 16px 24px;
            border-bottom: 1px solid rgba(255,255,255,0.04);
            font-size: 14px;
        }}
        tr:last-child td {{ border-bottom: none; }}
        tr:hover td {{ background: rgba(255,255,255,0.02); }}

        .badge {{
            background: rgba(34,197,94,0.15);
            color: #22c55e;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
        }}
        .rating-stars {{ color: #fbbf24; font-size: 13px; }}
        .no-orders {{
            text-align: center;
            padding: 48px;
            color: #475569;
        }}
        .refresh-btn {{
            background: rgba(255,255,255,0.1);
            border: none;
            color: white;
            padding: 8px 16px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 13px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <div>
            <h1>🍽️ AI Restaurant — Admin Dashboard</h1>
            <p>Real-time order management and analytics</p>
        </div>
        <div style="display:flex;gap:12px;align-items:center;">
            <button class="refresh-btn" onclick="location.reload()">🔄 Refresh</button>
            <div class="live-badge">
                <div class="live-dot"></div>
                Live
            </div>
        </div>
    </div>

    <div class="stats-grid">
        <div class="stat-card">
            <div class="icon">📦</div>
            <div class="value">{total_orders}</div>
            <div class="label">Total Orders</div>
        </div>
        <div class="stat-card">
            <div class="icon">💰</div>
            <div class="value">Rs.{total_revenue}</div>
            <div class="label">Total Revenue</div>
        </div>
        <div class="stat-card">
            <div class="icon">👥</div>
            <div class="value">{unique_customers}</div>
            <div class="label">Unique Customers</div>
        </div>
        <div class="stat-card">
            <div class="icon">⭐</div>
            <div class="value">{avg_rating}/5</div>
            <div class="label">Avg Rating</div>
        </div>
    </div>

    <div class="charts-grid">
        <div class="chart-card">
            <h3>📊 Top Ordered Items</h3>
            <canvas id="itemsChart" height="200"></canvas>
        </div>
        <div class="chart-card">
            <h3>💰 Revenue Overview</h3>
            <canvas id="revenueChart" height="200"></canvas>
        </div>
    </div>

    <div class="orders-card">
        <div class="orders-card-header">
            <h3>📋 All Orders</h3>
            <span class="orders-count">{total_orders} orders</span>
        </div>
        {"<table><tr><th>#</th><th>Customer</th><th>Phone</th><th>Items</th><th>Total</th><th>Rating</th><th>Time</th></tr>" + 
        "".join([f"<tr><td>{o.get('id','')}</td><td><b>{o.get('name','')}</b></td><td>{o.get('phone','')}</td><td>{', '.join(o.get('items',[]))}</td><td><span class='badge'>Rs.{o.get('total','')}</span></td><td><span class='rating-stars'>{'⭐' * o.get('rating',0)}</span></td><td>{o.get('time','')}</td></tr>" for o in reversed(orders)]) +
        "</table>" if orders else "<div class='no-orders'>No orders yet 🤖</div>"}
    </div>

    <script>
        const labels = {chart_labels};
        const values = {chart_values};

        if (labels.length > 0) {{
            new Chart(document.getElementById('itemsChart'), {{
                type: 'bar',
                data: {{
                    labels: labels,
                    datasets: [{{
                        label: 'Orders',
                        data: values,
                        backgroundColor: ['#667eea','#764ba2','#f093fb','#f5576c','#4facfe'],
                        borderRadius: 8,
                    }}]
                }},
                options: {{
                    plugins: {{ legend: {{ display: false }} }},
                    scales: {{
                        x: {{ ticks: {{ color: '#64748b' }}, grid: {{ color: 'rgba(255,255,255,0.05)' }} }},
                        y: {{ ticks: {{ color: '#64748b' }}, grid: {{ color: 'rgba(255,255,255,0.05)' }} }}
                    }}
                }}
            }});

            new Chart(document.getElementById('revenueChart'), {{
                type: 'doughnut',
                data: {{
                    labels: labels,
                    datasets: [{{
                        data: values,
                        backgroundColor: ['#667eea','#764ba2','#f093fb','#f5576c','#4facfe'],
                        borderWidth: 0,
                    }}]
                }},
                options: {{
                    plugins: {{
                        legend: {{
                            position: 'bottom',
                            labels: {{ color: '#94a3b8', padding: 16, font: {{ size: 12 }} }}
                        }}
                    }}
                }}
            }});
        }}
    </script>
</body>
</html>
"""
    return HTMLResponse(content=html)