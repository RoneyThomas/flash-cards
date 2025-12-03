
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Flashcard, Subject, Purchase, Classroom, ClassMembership
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

# Flashcards are now stored in the database

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

@app.route("/create_subject", methods=["GET", "POST"])
@login_required
def create_subject():
    # Get classrooms if teacher
    classrooms = []
    if current_user.role == 'teacher':
        classrooms = Classroom.query.filter_by(teacher_id=current_user.id).all()

    if request.method == "POST":
        name = request.form.get("name")
        classroom_id = request.form.get("classroom_id")
        
        if not name:
            flash("Subject name is required", "error")
            return render_template("create_subject.html", classrooms=classrooms)
            
        subject = Subject(name=name, user_id=current_user.id)
        
        if classroom_id and current_user.role == 'teacher':
             subject.classroom_id = classroom_id
        
        if current_user.role == 'admin':
            is_for_sale = request.form.get("is_for_sale") == 'on'
            price = request.form.get("price")
            if is_for_sale:
                subject.is_for_sale = True
                try:
                    subject.price = float(price)
                except (ValueError, TypeError):
                    subject.price = 0.0
        
        db.session.add(subject)
        db.session.commit()
        
        flash("Subject created successfully!", "success")
        return redirect(url_for('index'))
        
    return render_template("create_subject.html", classrooms=classrooms)

@app.route("/create_card", methods=["GET", "POST"])
@login_required
def create_card():
    subjects = Subject.query.filter_by(user_id=current_user.id).all()
    if not subjects:
        flash("Please create a subject first!", "error")
        return redirect(url_for('create_subject'))

    if request.method == "POST":
        question = request.form.get("question")
        answer = request.form.get("answer")
        subject_id = request.form.get("subject_id")
        
        if not question or not answer or not subject_id:
            flash("All fields are required", "error")
            return render_template("create_card.html", subjects=subjects)
            
        card = Flashcard(question=question, answer=answer, user_id=current_user.id, subject_id=subject_id)
        db.session.add(card)
        db.session.commit()
        
        flash("Flashcard created successfully!", "success")
        return redirect(url_for('create_card'))
        
    return render_template("create_card.html", subjects=subjects)

@app.route("/", methods=["GET"])
@login_required
def index():
    # Get created subjects
    created_subjects = Subject.query.filter_by(user_id=current_user.id).all()
    # Get purchased subjects
    purchased_purchases = Purchase.query.filter_by(user_id=current_user.id).all()
    purchased_subjects = [p.subject for p in purchased_purchases]
    
    classrooms = []
    class_subjects = []
    
    if current_user.role == 'teacher':
        classrooms = Classroom.query.filter_by(teacher_id=current_user.id).all()
    elif current_user.role == 'student':
        # Get subjects from enrolled classes
        for classroom in current_user.enrolled_classes:
            class_subjects.extend(classroom.subjects)
    
    return render_template("dashboard.html", 
                         subjects=created_subjects, 
                         purchased_subjects=purchased_subjects,
                         classrooms=classrooms,
                         class_subjects=class_subjects)

@app.route("/create_class", methods=["GET", "POST"])
@login_required
def create_class():
    if current_user.role != 'teacher':
        flash("Only teachers can create classes.", "error")
        return redirect(url_for('index'))
        
    if request.method == "POST":
        name = request.form.get("name")
        if not name:
            flash("Class name is required", "error")
            return render_template("create_class.html")
            
        classroom = Classroom(name=name, teacher_id=current_user.id)
        db.session.add(classroom)
        db.session.commit()
        
        flash("Class created successfully!", "success")
        return redirect(url_for('index'))
        
    return render_template("create_class.html")

@app.route("/class/<int:class_id>", methods=["GET", "POST"])
@login_required
def view_class(class_id):
    classroom = Classroom.query.get_or_404(class_id)
    
    if classroom.teacher_id != current_user.id:
        flash("Access denied.", "error")
        return redirect(url_for('index'))
        
    if request.method == "POST":
        email = request.form.get("email")
        student = User.query.filter_by(email=email).first()
        
        if not student:
            flash("User not found.", "error")
        elif student in classroom.students:
            flash("Student already in class.", "info")
        else:
            classroom.students.append(student)
            db.session.commit()
            flash(f"Added {student.username} to class.", "success")
            
    return render_template("view_class.html", classroom=classroom)

@app.route("/class/<int:class_id>/student/<int:student_id>")
@login_required
def view_student_progress(class_id, student_id):
    classroom = Classroom.query.get_or_404(class_id)
    
    if classroom.teacher_id != current_user.id:
        flash("Access denied.", "error")
        return redirect(url_for('index'))
        
    student = User.query.get_or_404(student_id)
    if student not in classroom.students:
        flash("Student not in this class.", "error")
        return redirect(url_for('view_class', class_id=class_id))
        
    subjects = Subject.query.filter_by(user_id=student.id).all()
    return render_template("student_progress.html", student=student, subjects=subjects, classroom=classroom)

@app.route("/study/<int:subject_id>", methods=["GET", "POST"])
def study(subject_id):
    subject = Subject.query.get_or_404(subject_id)
    
    # Check access: Owner OR Public OR Purchased OR Class Member
    has_access = False
    if subject.is_public:
        has_access = True
    elif current_user.is_authenticated:
        if subject.user_id == current_user.id:
            has_access = True
        elif subject.classroom_id:
            # Check if user is in the classroom
            classroom = Classroom.query.get(subject.classroom_id)
            if classroom and (current_user in classroom.students or classroom.teacher_id == current_user.id):
                has_access = True
        else:
            purchase = Purchase.query.filter_by(user_id=current_user.id, subject_id=subject_id).first()
            if purchase:
                has_access = True
    
    if not has_access:
        return render_template("study.html", 
                             subject=subject,
                             question="No flashcards found", 
                             answer="This subject has no cards yet.",
                             no_cards=True)

    cards = subject.flashcards
    if not cards:
        return render_template("study.html", 
                             subject=subject,
                             question="No flashcards found", 
                             answer="This subject has no cards yet.",
                             no_cards=True)

    if "current_card_id" not in session or "subject_id" not in session or session["subject_id"] != subject_id:
        card = random.choice(cards)
        session["current_card_id"] = card.id
        session["subject_id"] = subject_id
        session["show_answer"] = False
    
    current_card = Flashcard.query.get(session["current_card_id"])
    # Handle case where card might have been deleted
    if not current_card or current_card.subject_id != subject_id:
        card = random.choice(cards)
        session["current_card_id"] = card.id
        current_card = card
        session["show_answer"] = False

    if request.method == "POST":
        if "next" in request.form:
            card = random.choice(cards)
            session["current_card_id"] = card.id
            current_card = card
            session["show_answer"] = False
        elif "show" in request.form:
            session["show_answer"] = True

    return render_template("study.html",
                           subject=subject,
                           question=current_card.question,
                           answer=current_card.answer if session["show_answer"] else None)

@app.route("/subject/<int:subject_id>")
@login_required
def view_subject(subject_id):
    subject = Subject.query.get_or_404(subject_id)
    if subject.user_id != current_user.id and current_user.role != 'admin':
        flash("Access denied.", "error")
        return redirect(url_for('index'))
    return render_template("view_subject.html", subject=subject)

@app.route("/subject/<int:subject_id>/toggle_public", methods=["POST"])
@login_required
def toggle_public(subject_id):
    subject = Subject.query.get_or_404(subject_id)
    if subject.user_id != current_user.id:
        flash("Access denied.", "error")
        return redirect(url_for('index'))
    
    subject.is_public = not subject.is_public
    db.session.commit()
    status = "public" if subject.is_public else "private"
    flash(f"Subject is now {status}.", "success")
    return redirect(url_for('view_subject', subject_id=subject.id))

@app.route("/admin/users")
@login_required
def admin_users():
    if current_user.role != 'admin':
        flash("Access denied. Admin privileges required.", "error")
        return redirect(url_for('index'))
    
    users = User.query.all()
    return render_template("admin_users.html", users=users)

@app.route("/admin/subjects")
@login_required
def admin_subjects():
    if current_user.role != 'admin':
        flash("Access denied. Admin privileges required.", "error")
        return redirect(url_for('index'))
    
    subjects = Subject.query.all()
    return render_template("admin_subjects.html", subjects=subjects)

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

@app.route("/admin/users/change_role/<int:user_id>", methods=["POST"])
@login_required
def change_role(user_id):
    if current_user.role != 'admin':
        flash("Access denied. Admin privileges required.", "error")
        return redirect(url_for('index'))
    
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("You cannot change your own role.", "error")
        return redirect(url_for('admin_users'))
        
    new_role = request.form.get("role")
    if new_role not in ['student', 'teacher', 'admin']:
        flash("Invalid role selected.", "error")
        return redirect(url_for('admin_users'))
        
    user.role = new_role
    db.session.commit()
    flash(f"User {user.username}'s role changed to {new_role}.", "success")
    return redirect(url_for('admin_users'))

@app.route("/admin/subjects/delete/<int:subject_id>", methods=["POST"])
@login_required
def delete_subject(subject_id):
    if current_user.role != 'admin':
        flash("Access denied. Admin privileges required.", "error")
        return redirect(url_for('index'))
    
    subject = Subject.query.get_or_404(subject_id)
    db.session.delete(subject)
    db.session.commit()
    flash(f"Subject '{subject.name}' deleted successfully.", "success")
    return redirect(url_for('admin_subjects'))

@app.route("/admin/cards/delete/<int:card_id>", methods=["POST"])
@login_required
def delete_card(card_id):
    if current_user.role != 'admin':
        flash("Access denied. Admin privileges required.", "error")
        return redirect(url_for('index'))
    
    card = Flashcard.query.get_or_404(card_id)
    subject_id = card.subject_id
    db.session.delete(card)
    db.session.commit()
    flash("Flashcard deleted successfully.", "success")
    return redirect(url_for('view_subject', subject_id=subject_id))

if __name__ == "__main__":
    with app.app_context():
        db.create_all()  # Create database tables
    app.run(debug=True)