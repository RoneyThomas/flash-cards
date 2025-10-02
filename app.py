from flask import Flask, render_template, request, redirect, url_for, session
import random

app = Flask(__name__)
app.secret_key = "supersecretkey"  # Needed for session handling

# Flashcards stored as (question, answer)
flashcards = [
    ("Capital of France?", "Paris"),
    ("2 + 2 = ?", "4"),
    ("Largest planet?", "Jupiter")
]

@app.route("/", methods=["GET", "POST"])
def index():
    if "current_card" not in session:
        session["current_card"] = random.choice(flashcards)
        session["show_answer"] = False

    if request.method == "POST":
        if "next" in request.form:
            session["current_card"] = random.choice(flashcards)
            session["show_answer"] = False
        elif "show" in request.form:
            session["show_answer"] = True

    return render_template("index.html",
                           question=session["current_card"][0],
                           answer=session["current_card"][1] if session["show_answer"] else None)

if __name__ == "__main__":
    app.run(debug=True)
