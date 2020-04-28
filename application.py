import os

from flask import Flask, session, render_template, request
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


@app.route("/")
def index():
    return render_template("index.html")

@app.route("/Landing", methods=["POST"])
def Landing():
    username = request.form.get("Username")
    password = request.form.get("Password")
    print(f"{username} and {password}")
    if db.execute("SELECT * FROM logins WHERE username = :username", {"username": username}).rowcount == 0:
        db.execute("INSERT INTO logins (username,password) VALUES (:username, :password)",{"username": username, "password": password})
        db.commit()
        return f"Welcome to the Landing Page, we have created your account {username}"
    elif db.execute("SELECT * FROM logins WHERE username = :username", {"username": username}).rowcount == 1:
        login = db.execute("SELECT * FROM logins WHERE username = :username", {"username" : username}).fetchall()
        print(login)
        if login[0][1] == username and login[0][2] == password:
            return f"Welcome back to the landing page {username}"
        else:
            return f"{username} There has been an error, your password does not match your account."