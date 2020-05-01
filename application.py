import os

import requests
from flask import Flask, session, render_template, request, redirect, url_for, jsonify
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
    #Check if the user has already previously logged on. If they have send them to the landing page, else give them the option to register/login.
    if session.get("Username") != None:
        return redirect(url_for("Landing"))
    else:
        return render_template("Choose.html")

@app.route("/SignUp", methods=["POST","GET"])
def SignUp():
    #Run function if the way the user got here was from a post, otherwise send them to the normal sign up page.
    if request.method == "POST":
        username = request.form.get("Username")
        password = generate_password_hash(request.form.get("Password"))
        #Check if the username is registered, if it is not then send the user to Landing.html and add a new user to the database.
        if db.execute("SELECT * FROM logins WHERE username = :username", {"username":username}).rowcount == 0:
            session["Username"] = username
            db.execute("INSERT INTO logins (username,password) VALUES (:username, :password)",{"username":username, "password":password})
            db.commit()
            return render_template("Landing.html",username=username)
        #If the username is already registered, display the SignIn.html page with the error that the username has already been taken.
        elif db.execute("SELECT * FROM logins WHERE username = :username", {"username":username}).rowcount != 0:
            return render_template("SignIn.html",error="The username has been taken.")
        else:
        #If some error occurs render the basic error page.
            return render_template("Error.html",error="Error, something went wrong.")
    else:
        return render_template("SignIn.html")

@app.route("/LogIn", methods=["POST","GET"])
def LogIn():
    #Remove a previous sign-in if it exists.
    session.clear()
    #If the method to arrive was a Post take out the username/password input. If it was a Get then return the normal LogIn Page.
    if request.method == "POST":
        username = request.form.get("Username")
        password = request.form.get("Password")
        #If the username does not exist return the LogIn page with a unable to find username error.
        if db.execute("SELECT * FROM logins where username = :username", {"username":username}).rowcount == 0:
            return render_template("LogIn.html",error="We were unable to find an account with that username.")
        #If the username does exist then find information about it.
        else:
            userinfo = db.execute("SELECT password FROM logins WHERE username = :username", {"username":username}).fetchone()
            #if the username and password match, make the session's username the username inputted and also go to the landing page.
            if check_password_hash(userinfo["password"],password):
                session["Username"] = username
                return render_template("Landing.html",username=username)
            #if the password and username don't match then return the LogIn.html page with a mismatch error.
            elif not check_password_hash(userinfo["password"],password):
                return render_template("LogIn.html",error="The password does not apply to the username.")
            #If some random error occurs, provide the user with a default error page.
            else:
                return render_template("Error.html",error="Error, something went wrong.")
    else:
        return render_template("LogIn.html")

@app.route("/Landing", methods=["POST","GET"])
def Landing():
    #Check if the user posted information, or had a previously registered session to display the landing page. Otherwise take them back to the login.
    if request.method == "POST" or (request.method == "GET" and session["Username"]!= None):
        username = session["Username"]
        query = request.form.get("BookInfo")
        #If the query is present then find results.
        if query != None:
            results = db.execute("SELECT * from books WHERE isbn LIKE :query OR title LIKE :query OR author LIKE :query",{"query" : f"%{query}%"}).fetchall()
            #If no results are provided then render the landing page with an error saying that no results were found.
            if len(results)==0:
                return render_template("Landing.html",noreturn=True,username=username)
            #If results are found, render them in as a list.
            else:
                return render_template("Results.html", username=username, results=results)
        #If the user has no query, meaning they must have been brought here by the latter option on the if request then render the landing page.
        else:
            return render_template("Landing.html",username=session["Username"])
    #If the user simply arrives to this page without a post or previous session then inform them that an account is required to access the page.
    else:
        return render_template("Error.html",error="This page is inaccessable without an account.")
@app.route("/Landing/<string:book_isbn>", methods=["GET"])
def BookPage(book_isbn):
    #If the user arrives to this link without a username then return them to the choose login page.
    if session.get("Username") == None:
        return render_template("Choose.html")
    username = session["Username"]
    #Check if the user has commented previously, if so disable their ability to comment.
    if db.execute("SELECT * from ratings WHERE username = :username AND isbn = :isbn",{"username":username, "isbn" : book_isbn}).fetchone() == None:
        usercommented = 0
    elif db.execute("SELECT * from ratings WHERE username = :username AND isbn = :isbn",{"username":username, "isbn" : book_isbn}).fetchone() != None:
        usercommented = 1
    message = request.form.get("Message")
    rating = request.form.get("Rating")
    #If the user has placed a message, rating and has not previously commented then add their comment to the database.
    if message != None and rating != None and usercommented == 0:
        db.execute("INSERT INTO ratings (username,message,rating,isbn) VALUES (:username, :message, :rating, :isbn)",{"username" : username, "message" : message, "rating": rating, "isbn" : book_isbn})
        db.commit()
    #Recieve previous comments, general information regarding the book, the average rating on our website and the average rating on goodreads.
    comments = db.execute("SELECT * from ratings WHERE isbn = :isbn",{"isbn" : book_isbn}).fetchall()
    information = db.execute("SELECT * from books WHERE isbn = :isbn",{"isbn" : book_isbn}).fetchone()
    avgrate = db.execute("SELECT avg(rating) from ratings WHERE isbn = :isbn",{"isbn" : book_isbn}).fetchone()
    bookapi = requests.get("https://www.goodreads.com/book/review_counts.json",params={"key" : "4Uh6xEmtF0dIoI0q7anSg", "isbns": book_isbn})
    #Check if the API has returned information or if there was an error.
    if bookapi.status_code != 200:
        raise Exception("Error, API call unsuccessful")
    data = bookapi.json()
    bookrating = data["books"][0]["average_rating"]
    #Generate the BookPage.html and send to user.
    return render_template("BookPage.html", information=information, username=username, comments = comments, usercommented = usercommented, avgrate = avgrate, gbooks = bookrating)
@app.route("/LogOut")
def Logout():
    #Once the user clicks the log out button, clear their session data and send them to the Choose Login page with a message indicating they have logged out.
    session.clear()
    return render_template("Choose.html",LogOut=True)
@app.route("/api/<string:book_isbn>")
def BookApi(book_isbn):
    #Fetch the information of the book from our database as well as the data from the goodreads api.
    bookinfo = db.execute("SELECT * from books where isbn = :isbn",{"isbn":book_isbn}).fetchone()
    bookapi = requests.get("https://www.goodreads.com/book/review_counts.json",params={"key" : "4Uh6xEmtF0dIoI0q7anSg", "isbns": book_isbn}).json()
    #If we are unable to find bookinfo then the ISBN is not registered with our webpage and will return a 404 error.
    if bookinfo == None:
        return jsonify({"error": "Invalid book ISBN"}), 404
    #If the ISBN is found then return the title, author, year and ISBN from our webpage and the review_count and average_score from the api.
    return jsonify({
        "title": bookinfo["title"],
        "author": bookinfo["author"],
        "year": bookinfo["year"],
        "isbn": book_isbn,
        "review_count": bookapi["books"][0]["reviews_count"],
        "average_score": bookapi["books"][0]["average_rating"]
    })