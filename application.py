import os

import requests
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
    if username != None and password != None:
        if db.execute("SELECT * FROM logins WHERE username = :username", {"username": username}).rowcount == 0:
            db.execute("INSERT INTO logins (username,password) VALUES (:username, :password)",{"username": username, "password": password})
            db.commit()
            session["Username"] = username
            return render_template("Landing.html", username=username)
        elif db.execute("SELECT * FROM logins WHERE username = :username", {"username": username}).rowcount == 1:
            login = db.execute("SELECT * FROM logins WHERE username = :username", {"username" : username}).fetchall()
            print(login)
            if login[0][1] == username and login[0][2] == password:
                return render_template("Landing.html", username=username)
                session["Username"] = username
            else:
                return f"{username} There has been an error, your password does not match your account."
    else:
        username = session["Username"]
        query = request.form.get("BookInfo")
        results = db.execute("SELECT * from books WHERE isbn LIKE :query OR title LIKE :query OR author LIKE :query",{"query" : f"%{query}%"}).fetchall()
        if len(results)==0:
            return f"{username} we were unable to find any result associated with your search, please try again."
        else:
            return render_template("Results.html", username=username, results=results)
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
    print(data)
    bookrating = data["books"][0]["average_rating"]
    return render_template("BookPage.html", information=information, username=username, comments = comments, usercommented = usercommented, avgrate = avgrate, gbooks = bookrating)
