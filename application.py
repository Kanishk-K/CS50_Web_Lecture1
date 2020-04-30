import os

import requests
from flask import Flask, session, render_template, request, redirect, url_for
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from werkzeug.security import check_password_hash, generate_password_hash

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
    if session.get("Username") != None:
        return redirect(url_for("Landing"))
    else:
        return render_template("Choose.html")

@app.route("/SignUp", methods=["POST","GET"])
def SignUp():
    if request.method == "POST":
        username = request.form.get("Username")
        password = generate_password_hash(request.form.get("Password"))
        if db.execute("SELECT * FROM logins WHERE username = :username", {"username":username}).rowcount == 0:
            session["Username"] = username
            db.execute("INSERT INTO logins (username,password) VALUES (:username, :password)",{"username":username, "password":password})
            db.commit()
            return render_template("Landing.html",username=username)
        elif db.execute("SELECT * FROM logins WHERE username = :username", {"username":username}).rowcount != 0:
            return render_template("SignIn.html",error="The username has been taken.")
        else:
            return render_template("Error.html",error="Error, something went wrong.")
    else:
        return render_template("SignIn.html")

@app.route("/LogIn", methods=["POST","GET"])
def LogIn():
    session.clear()
    if request.method == "POST":
        username = request.form.get("Username")
        password = request.form.get("Password")
        if db.execute("SELECT * FROM logins where username = :username", {"username":username}).rowcount == 0:
            return render_template("LogIn.html",error="We were unable to find an account with that username.")
        else:
            userinfo = db.execute("SELECT password FROM logins WHERE username = :username", {"username":username}).fetchone()
            if check_password_hash(userinfo["password"],password):
                session["Username"] = username
                return render_template("Landing.html",username=username)
            elif not check_password_hash(userinfo["password"],password):
                return render_template("LogIn.html",error="The password does not apply to the username.")
            else:
                return render_template("Error.html",error="Error, something went wrong.")
    else:
        return render_template("LogIn.html")

@app.route("/Landing", methods=["POST","GET"])
def Landing():
    if request.method == "POST" or (request.method == "GET" and session["Username"]!= None):
        username = session["Username"]
        query = request.form.get("BookInfo")
        if query != None:
            results = db.execute("SELECT * from books WHERE isbn LIKE :query OR title LIKE :query OR author LIKE :query",{"query" : f"%{query}%"}).fetchall()
            if len(results)==0:
                return render_template("Landing.html",noreturn=True,username=username)
            else:
                return render_template("Results.html", username=username, results=results)
        else:
            return render_template("Landing.html",username=session["Username"])
    else:
        return render_template("Error.html",error="This page is inaccessable without an account.")
@app.route("/Landing/<string:book_isbn>", methods=["POST","GET"])
def BookPage(book_isbn):
    username = session["Username"]
    if db.execute("SELECT * from ratings WHERE username = :username AND isbn = :isbn",{"username":username, "isbn" : book_isbn}).fetchone() == None:
        usercommented = 0
    elif db.execute("SELECT * from ratings WHERE username = :username AND isbn = :isbn",{"username":username, "isbn" : book_isbn}).fetchone() != None:
        usercommented = 1
    message = request.form.get("Message")
    rating = request.form.get("Rating")
    if message != None and rating != None and usercommented == 0:
        db.execute("INSERT INTO ratings (username,message,rating,isbn) VALUES (:username, :message, :rating, :isbn)",{"username" : username, "message" : message, "rating": rating, "isbn" : book_isbn})
        db.commit()
    comments = db.execute("SELECT * from ratings WHERE isbn = :isbn",{"isbn" : book_isbn}).fetchall()
    information = db.execute("SELECT * from books WHERE isbn = :isbn",{"isbn" : book_isbn}).fetchone()
    avgrate = db.execute("SELECT avg(rating) from ratings WHERE isbn = :isbn",{"isbn" : book_isbn}).fetchone()
    bookapi = requests.get("https://www.goodreads.com/book/review_counts.json",params={"key" : "4Uh6xEmtF0dIoI0q7anSg", "isbns": book_isbn})
    if bookapi.status_code != 200:
        raise Exception("Error, API call unsuccessful")
    data = bookapi.json()
    bookrating = data["books"][0]["average_rating"]
    return render_template("BookPage.html", information=information, username=username, comments = comments, usercommented = usercommented, avgrate = avgrate, gbooks = bookrating)
@app.route("/LogOut")
def Logout():
    session.clear()
    return render_template("Choose.html",LogOut=True)