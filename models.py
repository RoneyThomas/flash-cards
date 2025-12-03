from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    """User model for authentication."""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(10), nullable=False, default='student')

    def set_password(self, password):
        """Hash and set the user's password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Check if the provided password matches the hash."""
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

class Flashcard(db.Model):
    """Flashcard model."""
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    
    user = db.relationship('User', backref=db.backref('flashcards', lazy=True))

    def __repr__(self):
        return f'<Flashcard {self.question[:20]}...>'

class Subject(db.Model):
    """Subject/Set model for grouping flashcards."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    classroom_id = db.Column(db.Integer, db.ForeignKey('classroom.id'), nullable=True)
    is_public = db.Column(db.Boolean, default=False)
    
    user = db.relationship('User', backref=db.backref('subjects', lazy=True))
    classroom = db.relationship('Classroom', backref=db.backref('subjects', lazy=True))
    flashcards = db.relationship('Flashcard', backref='subject', lazy=True, cascade="all, delete-orphan")
    price = db.Column(db.Float, default=0.0)
    is_for_sale = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f'<Subject {self.name}>'

class Purchase(db.Model):
    """Model to track purchased subjects."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    purchase_date = db.Column(db.DateTime, server_default=db.func.now())

    user = db.relationship('User', backref=db.backref('purchases', lazy=True))
    subject = db.relationship('Subject', backref=db.backref('purchases', lazy=True))

class Classroom(db.Model):
    """Classroom model for teachers."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    teacher = db.relationship('User', backref=db.backref('classrooms', lazy=True))
    students = db.relationship('User', secondary='class_membership', backref=db.backref('enrolled_classes', lazy=True))

    def __repr__(self):
        return f'<Classroom {self.name}>'

class ClassMembership(db.Model):
    """Association table for students in classes."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    classroom_id = db.Column(db.Integer, db.ForeignKey('classroom.id'), nullable=False)

    def __repr__(self):
        # Assuming 'name' refers to the classroom name for a meaningful representation
        # This would require accessing the related classroom object.
        # For simplicity, let's represent by IDs for now.
        return f'<ClassMembership User:{self.user_id} Class:{self.classroom_id}>'
