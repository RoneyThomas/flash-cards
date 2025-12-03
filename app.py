from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User
import random
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "supersecretkey")  # Needed for session handling

# Configure SQLAlchemy
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///flashcards.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db.init_app(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Flashcards stored as (question, answer)
flashcards = [
    ("Capital of France?", "Paris"),
    ("2 + 2 = ?", "4"),
    ("Largest planet?", "Jupiter")
]

@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")
        role = request.form.get("role")
        
        # Validation
        if not username or not email or not password or not role:
            flash("All fields are required", "error")
            return render_template("register.html")
        
        if role not in ['student', 'teacher', 'admin']:
            flash("Invalid role selected", "error")
            return render_template("register.html")
        
        if password != confirm_password:
            flash("Passwords do not match", "error")
            return render_template("register.html")
        
        # Check if user already exists
        if User.query.filter_by(username=username).first():
            flash("Username already exists", "error")
            return render_template("register.html")
        
        if User.query.filter_by(email=email).first():
            flash("Email already exists", "error")
            return render_template("register.html")
        
        # Create new user
        user = User(username=username, email=email, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        flash("Registration successful! Please login.", "success")
        return redirect(url_for('login'))
    
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            flash("Invalid username or password", "error")
    
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out", "success")
    return redirect(url_for('login'))

@app.route("/", methods=["GET", "POST"])
@login_required
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

@app.route("/admin/users")
@login_required
def admin_users():
    if current_user.role != 'admin':
        flash("Access denied. Admin privileges required.", "error")
        return redirect(url_for('index'))
    
    users = User.query.all()
    return render_template("admin_users.html", users=users)

@app.route("/admin/users/delete/<int:user_id>", methods=["POST"])
@login_required
def delete_user(user_id):
    if current_user.role != 'admin':
        flash("Access denied. Admin privileges required.", "error")
        return redirect(url_for('index'))
    
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("You cannot delete yourself.", "error")
        return redirect(url_for('admin_users'))
        
    db.session.delete(user)
    db.session.commit()
    flash(f"User {user.username} deleted successfully.", "success")
    return redirect(url_for('admin_users'))

if __name__ == "__main__":
    with app.app_context():
        db.create_all()  # Create database tables
    app.run(debug=True)