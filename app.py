from flask import Flask, request, redirect, session

#================ CONFIG =================#

app = Flask(__name__)
app.secret_key = "okx123"

PANEL_PASSWORD = "1234"

#================ LOGIN =================#

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        password = request.form.get("password", "").strip()

        if password == PANEL_PASSWORD:
            session["auth"] = True
            return redirect("/")
        return "Senha incorreta"

    return """
    <h2>Login Painel BOT</h2>
    <form method="post">
        <input type="password" name="password" placeholder="senha">
        <button type="submit">Entrar</button>
    </form>
    """

def auth():
    return session.get("auth", False)

#================ PAINEL =================#

@app.route("/")
def home():
    if not auth():
        return redirect("/login")

    return """
    <h1>PAINEL OKX BOT (TESTE)</h1>

    <p>Preço: 1000</p>
    <p>Tendência: UP</p>
    <p>Posição: False</p>

    <hr>

    <a href="/buy"><button>BUY</button></a>
    <a href="/sell"><button>SELL</button></a>

    <hr>

    <a href="/logout">Logout</a>
    """

#================ AÇÕES =================#

@app.route("/buy")
def buy():
    if not auth():
        return redirect("/login")
    return "BUY executado (teste)"


@app.route("/sell")
def sell():
    if not auth():
        return redirect("/login")
    return "SELL executado (teste)"

#================ LOGOUT =================#

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")