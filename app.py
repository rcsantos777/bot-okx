from flask import Flask, request, redirect, session
import requests, os, time, hmac, base64, json
import pandas as pd
import threading

#================ CONFIG =================#

API_KEY = os.getenv("OKX_API_KEY")
API_SECRET = os.getenv("OKX_API_SECRET")
PASSPHRASE = os.getenv("OKX_API_PASSPHRASE")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

BASE_URL = "https://www.okx.com"
SYMBOL = "ETH-USDT"

EMA_PERIOD = 50
RR = 2

app = Flask(__name__)
app.secret_key = "okx123"

PANEL_PASSWORD = "1234"
trades = []

#================ TELEGRAM =================#

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg})
    except:
        pass

#================ AUTH OKX =================#

def sign(method, path, body=""):
    try:
        ts = str(time.time())
        msg = ts + method + path + body

        signature = base64.b64encode(
            hmac.new(API_SECRET.encode(), msg.encode(), "sha256").digest()
        ).decode()

        return {
            "OK-ACCESS-KEY": API_KEY,
            "OK-ACCESS-SIGN": signature,
            "OK-ACCESS-TIMESTAMP": ts,
            "OK-ACCESS-PASSPHRASE": PASSPHRASE,
            "Content-Type": "application/json"
        }
    except:
        return {}

#================ MARKET =================#

def price():
    try:
        r = requests.get(f"{BASE_URL}/api/v5/market/ticker?instId={SYMBOL}").json()
        return float(r['data'][0]['last'])
    except:
        return 0

def trend():
    try:
        r = requests.get(f"{BASE_URL}/api/v5/market/candles?instId={SYMBOL}&bar=5m&limit=100").json()
        df = pd.DataFrame(r['data'])
        df = df.iloc[::-1]
        df['close'] = df[4].astype(float)
        ema = df['close'].ewm(span=EMA_PERIOD).mean()
        return "UP" if df['close'].iloc[-1] > ema.iloc[-1] else "DOWN"
    except:
        return "UNKNOWN"

#================ POSITION =================#

def has_position():
    try:
        r = requests.get(BASE_URL+"/api/v5/account/positions", headers=sign("GET","/api/v5/account/positions")).json()
        for p in r.get("data", []):
            if float(p.get("pos", 0)) != 0:
                return True
        return False
    except:
        return False

#================ ORDER =================#

def place_order(side):
    try:
        path = "/api/v5/trade/order"
        p = price()

        body = {
            "instId": SYMBOL,
            "tdMode": "cash",
            "side": "buy" if side=="BUY" else "sell",
            "ordType": "market",
            "sz": "0.01"
        }

        res = requests.post(BASE_URL+path, headers=sign("POST",path,json.dumps(body)), data=json.dumps(body)).json()

        trades.append({"side": side, "price": p})

        send_telegram(f"{side} executado | preco {p}")

        return res
    except Exception as e:
        return {"error": str(e)}

#================ AUTO BOT =================#

def auto_bot():
    while True:
        try:
            if not has_position():
                t = trend()

                if t == "UP":
                    place_order("BUY")

                elif t == "DOWN":
                    place_order("SELL")

        except:
            pass

        time.sleep(60)  # roda a cada 1 minuto

threading.Thread(target=auto_bot).start()

#================ LOGIN =================#

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method=="POST":
        if request.form.get("password","").strip()==PANEL_PASSWORD:
            session["auth"]=True
            return redirect("/")
        return "Senha incorreta"

    return """
    <h2>Login</h2>
    <form method="post">
    <input type="password" name="password">
    <button>Entrar</button>
    </form>
    """

def auth():
    return session.get("auth", False)

#================ PAINEL =================#

@app.route("/")
def home():
    if not auth():
        return redirect("/login")

    return f"""
    <h1>BOT OKX AUTO</h1>

    Preco: {price()} <br>
    Tendencia: {trend()} <br>
    Posicao: {has_position()} <br>
    Trades: {len(trades)} <br><br>

    <a href="/buy"><button>BUY</button></a>
    <a href="/sell"><button>SELL</button></a>
    <br><br>
    <a href="/logout">Logout</a>
    """

#================ MANUAL =================#

@app.route("/buy")
def buy():
    return str(place_order("BUY"))

@app.route("/sell")
def sell():
    return str(place_order("SELL"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")