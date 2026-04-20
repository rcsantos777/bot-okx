from flask import Flask, request, redirect, session
import requests
import os
import time
import hmac
import base64
import json
import pandas as pd

#================ CONFIG =================#

API_KEY = os.getenv("OKX_API_KEY")
API_SECRET = os.getenv("OKX_API_SECRET")
PASSPHRASE = os.getenv("OKX_API_PASSPHRASE")

BASE_URL = "https://www.okx.com"
SYMBOL = "ETH-USDT"

EMA_PERIOD = 50
RR = 2

app = Flask(__name__)
app.secret_key = "change_this_secret"

PANEL_PASSWORD = "abcd"

#================ AUTH OKX =================#

def sign(method, path, body=""):
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

#================ MARKET =================#

def price():
    url = f"{BASE_URL}/api/v5/market/ticker?instId={SYMBOL}"
    return float(requests.get(url).json()['data'][0]['last'])


def trend():
    url = f"{BASE_URL}/api/v5/market/candles?instId={SYMBOL}&bar=5m&limit=100"
    r = requests.get(url).json()

    df = pd.DataFrame(r['data'])
    df = df.iloc[::-1]
    df['close'] = df[4].astype(float)

    ema = df['close'].ewm(span=EMA_PERIOD).mean()

    return "UP" if df['close'].iloc[-1] > ema.iloc[-1] else "DOWN"

#================ POSITION =================#

def has_position():
    path = "/api/v5/account/positions"
    r = requests.get(BASE_URL + path, headers=sign("GET", path)).json()

    for p in r.get("data", []):
        if float(p.get("pos", 0)) != 0:
            return True
    return False

#================ ORDER =================#

def place_order(side):
    path = "/api/v5/trade/order"

    p = price()
    risk = p * 0.005

    sl = p - risk if side == "BUY" else p + risk
    tp = p + (risk * RR) if side == "BUY" else p - (risk * RR)

    body = {
        "instId": SYMBOL,
        "tdMode": "cash",
        "side": "buy" if side == "BUY" else "sell",
        "ordType": "market",
        "sz": "0.01",
        "attachAlgoOrds": [
            {
                "tpTriggerPx": str(tp),
                "tpOrdPx": "-1",
                "slTriggerPx": str(sl),
                "slOrdPx": "-1"
            }
        ]
    }

    return requests.post(
        BASE_URL + path,
        headers=sign("POST", path, json.dumps(body)),
        data=json.dumps(body)
    ).json()

#================ LOGIN =================#

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form.get("password") == PANEL_PASSWORD:
            session["auth"] = True
            return redirect("/")
        return "Senha incorreta"

    return """
    <h2>Login Painel Bot</h2>
    <form method="post">
        <input type="password" name="password" placeholder="senha">
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
    <h1> PAINEL OKX BOT</h1>

    <p><b>Preço:</b> {price()}</p>
    <p><b>Tendência:</b> {trend()}</p>
    <p><b>Posição:</b> {has_position()}</p>

    <hr>

    <a href="/buy"><button style="font-size:20px;color:green;"> BUY</button></a>
    <a href="/sell"><button style="font-size:20px;color:red;"> SELL</button></a>

    <hr>

    <a href="/logout">Sair</a>
    """

#================ ACTIONS =================#

@app.route("/buy")
def buy():
    if not auth():
        return redirect("/login")

    if has_position():
        return " Já existe posição"

    if trend() != "UP":
        return " Contra tendência"

    return str(place_order("BUY"))


@app.route("/sell")
def sell():
    if not auth():
        return redirect("/login")

    if has_position():
        return " Já existe posição"

    if trend() != "DOWN":
        return " Contra tendência"

    return str(place_order("SELL"))

#================ LOGOUT =================#

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")