import os
from datetime import datetime

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    userId = session["user_id"]
    db.execute("DELETE FROM shares WHERE user_id = ? AND shares = 0", userId)
    userInfo = db.execute("SELECT * FROM shares WHERE user_id = ?", userId)
    userCash = db.execute("SELECT cash FROM users WHERE id = ?", userId)
    userCash = round(userCash[0]["cash"],2)
    currentSymbol = []
    length = len(userInfo)
    counter = 0
    for row in userInfo:
        currentSymbol.append(lookup(userInfo[counter]["symbol"]))
        counter += 1
    return render_template("index.html", userInfo=userInfo, currentSymbol=currentSymbol, length=length, userCash=userCash)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if (request.method == "GET"):
        priceToBuy = 0
        return render_template("buy.html", pricetoBuy=priceToBuy)
    elif (request.method == "POST"):
        # Stores the users information to check if transaction is valid
        symbolToBuy = lookup(request.form.get("symbol"))
         # Checks if Symbol was submitted
        if not symbolToBuy:
            return apology("You must submit a symbol")

        sharesToBuy = request.form.get("shares")
        priceToBuy = float(symbolToBuy["price"]) * float(sharesToBuy)
        userId = session["user_id"]
        userInfo = db.execute("SELECT * FROM users WHERE id = :userid", userid=userId)
        cash = userInfo[0]["cash"]
        date = datetime.now()

        # Checks if user can pay for the shares
        if (priceToBuy > cash):
            return apology("Not enough money")

        else:
            cash = cash - priceToBuy
            # Inserts transaction into user's history
            db.execute("INSERT INTO history (symbol, date, price, total, shares, user_id) VALUES (?, ?, ?, ?, ?, ?)",
                        symbolToBuy["symbol"], date, symbolToBuy["price"], priceToBuy, sharesToBuy, userId)
            # Updates the user's cash availability
            db.execute("UPDATE users SET cash = ? WHERE id = ?",
                        cash, userId)
            checkSymbol = db.execute("SELECT symbol, shares FROM shares WHERE symbol = ? AND user_id = ?", symbolToBuy["symbol"], userId)

            # Checks if the user has shares from this same symbol to update db
            if len(checkSymbol) == 1:
                # List of user's info on the same symbol to be bought
                shareInfo = db.execute("SELECT SUM(shares), SUM(total) FROM shares WHERE symbol = ? AND user_id = ?",
                                        symbolToBuy["symbol"], userId)
                shareCount = int(shareInfo[0]["SUM(shares)"]) + int(sharesToBuy)
                totalCount = float(shareInfo[0]["SUM(total)"]) + float(priceToBuy)
                # Updates the number of shares base on the recent purchase
                db.execute("UPDATE shares SET shares = ?, total = ? WHERE symbol = ? AND user_id = ?",
                            shareCount, totalCount, symbolToBuy["symbol"], userId)
                return redirect("/")

            else:
                # If the user doesn't have shares of this symbol, insert a new row
                db.execute("INSERT INTO shares (user_id, shares, symbol, total) VALUES (?, ?, ?, ?)",
                            userId, sharesToBuy, symbolToBuy["symbol"], priceToBuy)
                return redirect("/")

@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    userId = session["user_id"]
    userHistory = db.execute("SELECT * FROM history WHERE user_id = ? AND symbol IS NOT NULL ORDER BY date DESC", userId)
    length = len(userHistory)
    counter = 0
    for row in userHistory:
        print(userHistory[counter]["symbol"])
        counter += 1
    return render_template("history.html", userHistory=userHistory, length=length)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if (request.method == "GET"):
       return render_template("quote.html")

    if (request.method == "POST"):
        symbol = lookup(request.form.get("symbol"))
        if not symbol:
            notfound = request.form.get("symbol") + "was not found"
            return render_template("quote.html", notfound=notfound)
        else:
            return render_template("quoted.html", symbol=symbol)

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if (request.method == "GET"):
        return render_template("register.html")

    if (request.method == "POST"):

        # Ensure that a username is submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)
        # Ensure that the password and confirmation are submitted and ensure that both are the same value
        elif not request.form.get("password"):
            return apology("must provide password", 403)
        elif not request.form.get("confirmPassword"):
            return apology("must provide password confirmation", 403)
        elif (request.form.get("password") != request.form.get("confirmPassword")):
            return apology("password did not match password confirmation", 403)

        # Insert user in the db
        username = request.form.get("username")
        passHash = generate_password_hash(request.form.get("password"))

        # Check if username is already taken
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))
        if len(rows) == 1:
            return apology("this username has already been taken", 403)
        else:
            db.execute("INSERT INTO users (username, hash) VALUES(?, ?)",
                        username, passHash)
            userId = db.execute("SELECT id FROM users WHERE username = :username",
                                 username=username)
            db.execute("INSERT INTO history (user_id) VALUES(?)",
                        userId[0]["id"])

        login()
        return redirect("/")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    userId = session["user_id"]
    if (request.method == "GET"):
        userSymbols = db.execute("SELECT symbol FROM shares WHERE user_id = ?", userId)
        length = len(userSymbols)
        return render_template("sell.html", userSymbols=userSymbols, length=length)
    if (request.method == "POST"):
        sharesToSell = request.form.get("shares")
        symbolToSell = request.form.get("symbol")
        actualPrice = lookup(symbolToSell)
        actualPrice = actualPrice["price"]
        userShares = db.execute("SELECT shares FROM shares WHERE user_id = ? AND symbol = ?", userId, symbolToSell)
        userShares = userShares[0]["shares"]
        sharesToSell = int(sharesToSell)
        if (sharesToSell > userShares):
            return apology("Not enough shares to sell")
        else:
            totalValue = sharesToSell * actualPrice
            updatedShares = userShares - sharesToSell
            userCash = db.execute("SELECT cash FROM users WHERE id = ?", userId)
            userCash = round(userCash[0]["cash"], 2)
            userCash = round((userCash + totalValue), 2)
            print(userCash)
            remaining = round((updatedShares * actualPrice), 2)
            print(remaining)
            db.execute("UPDATE shares SET shares = ?, total = ? WHERE symbol = ? AND user_id = ?",
                        updatedShares, remaining, symbolToSell, userId)
            db.execute("UPDATE users SET cash = ? WHERE id = ?", userCash, userId)
            date = datetime.now()
            soldShare = sharesToSell * -1
            print(soldShare)
            db.execute("INSERT INTO history (symbol, date, price, total, shares, user_id) VALUES (?, ?, ?, ?, ?, ?)",
                        symbolToSell, date, actualPrice, totalValue, soldShare, userId)
            return redirect("/")
def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
