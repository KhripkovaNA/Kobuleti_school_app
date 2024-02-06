from app import db, login
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime


parent_child_table = db.Table(
    'parent_child_table',
    db.Column('parent_id', db.Integer, db.ForeignKey('persons.id')),
    db.Column('child_id', db.Integer, db.ForeignKey('persons.id')),
    db.Column('relation', db.String(50))
)


student_subject_table = db.Table(
    'student_subject_table',
    db.Column('student_id', db.Integer, db.ForeignKey('persons.id')),
    db.Column('subject_id', db.Integer, db.ForeignKey('subjects.id'))
)


teacher_subject_table = db.Table(
    'teacher_subject_table',
    db.Column('teacher_id', db.Integer, db.ForeignKey('persons.id')),
    db.Column('subject_id', db.Integer, db.ForeignKey('subjects.id'))
)


subscription_types_table = db.Table(
    'subscription_types_table',
    db.Column('subscription_types_id', db.Integer, db.ForeignKey('subscription_types.id')),
    db.Column('subject_id', db.Integer, db.ForeignKey('subjects.id'))
)

student_lesson_registered_table = db.Table(
    'student_lesson_registered_table',
    db.Column('student_id', db.Integer, db.ForeignKey('persons.id')),
    db.Column('lesson_id', db.Integer, db.ForeignKey('lessons.id'))
)

student_lesson_attended_table = db.Table(
    'student_lesson_attended_table',
    db.Column('student_id', db.Integer, db.ForeignKey('persons.id')),
    db.Column('lesson_id', db.Integer, db.ForeignKey('lessons.id')),
    db.Column('attending_status', db.String(50))
)

class_lesson_table = db.Table(
    'class_lesson_table',
    db.Column('class_id', db.Integer, db.ForeignKey('school_classes.id')),
    db.Column('lesson_id', db.Integer, db.ForeignKey('lessons.id'))
)

teacher_class_table = db.Table(
    'teacher_class_table',
    db.Column('class_id', db.Integer, db.ForeignKey('school_classes.id')),
    db.Column('teacher_id', db.Integer, db.ForeignKey('persons.id')),
    db.Column('main_teacher', db.Boolean, default=False)
)

subject_class_table = db.Table(
    'subject_class_table',
    db.Column('class_id', db.Integer, db.ForeignKey('school_classes.id')),
    db.Column('subject_id', db.Integer, db.ForeignKey('subjects.id'))
)


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))

    def __repr__(self):
        return f'<User {self.username}>'

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


@login.user_loader
def load_user(id):
    return User.query.get(int(id))


class Person(db.Model):
    __tablename__ = 'persons'

    id = db.Column(db.Integer, primary_key=True)
    last_name = db.Column(db.String(50))
    first_name = db.Column(db.String(50))
    patronym = db.Column(db.String(50), default="")
    dob = db.Column(db.Date)
    person_type = db.Column(db.String(16))
    status = db.Column(db.String(50))
    teacher = db.Column(db.Boolean, default=False)
    color = db.Column(db.String(16))
    leaving_reason = db.Column(db.String(120), default="")
    pause_until = db.Column(db.Date)
    comment = db.Column(db.String(120), default="")
    primary_contact = db.Column(db.Integer, db.ForeignKey('persons.id'))

    subjects = db.relationship('Subject', secondary=student_subject_table,
                               backref='students', lazy='dynamic')
    subjects_taught = db.relationship('Subject', secondary=teacher_subject_table,
                                      backref='teachers', lazy='dynamic')
    subscriptions = db.relationship('Subscription', backref='student', lazy='dynamic')
    school_class_id = db.Column(db.Integer, db.ForeignKey('school_classes.id'))

    parents = db.relationship('Person', secondary=parent_child_table,
                              primaryjoin=(parent_child_table.c.child_id == id),
                              secondaryjoin=(parent_child_table.c.parent_id == id),
                              backref=db.backref('children', lazy='dynamic'), lazy='dynamic')
    balance = db.Column(db.Numeric(8, 2), default=0)

    def __repr__(self):
        return f"<Person {self.id}: {self.last_name} {self.first_name}>"


class Contact(db.Model):
    __tablename__ = 'contacts'

    id = db.Column(db.Integer, primary_key=True)
    person_id = db.Column(db.Integer, db.ForeignKey('persons.id'), unique=True)
    telegram = db.Column(db.String(50), default="")
    phone = db.Column(db.String(50), default="")
    other_contact = db.Column(db.String(64), default="")
    person = db.relationship('Person', backref='contacts', uselist=False)


class Subject(db.Model):
    __tablename__ = 'subjects'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    short_name = db.Column(db.String(50))
    description = db.Column(db.String(120), default="")
    one_time_price = db.Column(db.Numeric(8, 2))
    school_price = db.Column(db.Numeric(8, 2))
    subscription_types = db.relationship('SubscriptionType', secondary=subscription_types_table,
                                         backref='subjects', lazy='dynamic')
    subject_type_id = db.Column(db.Integer, db.ForeignKey('subject_types.id'))
    subject_type = db.relationship('SubjectType', backref='subjects')
    subscriptions = db.relationship('Subscription', backref='subject')

    def __repr__(self):
        return f"<Subject {self.id}: {self.name}>"


class Subscription(db.Model):
    __tablename__ = 'subscriptions'

    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'))
    student_id = db.Column(db.Integer, db.ForeignKey('persons.id'))
    subscription_type_id = db.Column(db.Integer, db.ForeignKey('subscription_types.id'))
    lessons_left = db.Column(db.Integer)
    purchase_date = db.Column(db.Date, default=datetime.today().date())
    end_date = db.Column(db.Date)
    active = db.Column(db.Boolean, default=False)


class SubscriptionType(db.Model):
    __tablename__ = 'subscription_types'

    id = db.Column(db.Integer, primary_key=True)
    lessons = db.Column(db.Integer)
    period = db.Column(db.String(50), default="")
    duration = db.Column(db.Integer)
    price = db.Column(db.Numeric(8, 2))
    subscriptions = db.relationship('Subscription', backref='subscription_type')


class Room(db.Model):
    __tablename__ = 'rooms'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    color = db.Column(db.String(16))

    def __repr__(self):
        return f"<Room {self.id}: {self.name}>"


class Lesson(db.Model):
    __tablename__ = 'lessons'

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date)
    start_time = db.Column(db.Time)
    end_time = db.Column(db.Time)
    lesson_completed = db.Column(db.Boolean, default=False)
    lesson_topic = db.Column(db.String(120), default="")

    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'))
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'))
    teacher_id = db.Column(db.Integer, db.ForeignKey('persons.id'))
    lesson_type_id = db.Column(db.Integer, db.ForeignKey('subject_types.id'))

    room = db.relationship('Room', backref='lessons')
    subject = db.relationship('Subject', backref='lessons')
    teacher = db.relationship('Person', backref='lessons')
    lesson_type = db.relationship('SubjectType', backref='lessons')

    school_classes = db.relationship('SchoolClass', secondary=class_lesson_table,
                                     backref='class_lessons', lazy='dynamic')

    students_registered = db.relationship('Person', secondary=student_lesson_registered_table,
                                          backref='lessons_registered', lazy='dynamic')
    students_attended = db.relationship('Person', secondary=student_lesson_attended_table,
                                        backref='lessons_attended', lazy='dynamic')


class SchoolClass(db.Model):
    __tablename__ = 'school_classes'

    id = db.Column(db.Integer, primary_key=True)
    school_class = db.Column(db.Integer)
    school_name = db.Column(db.String(50))
    school_students = db.relationship('Person', backref='school_class', lazy='dynamic')
    school_teachers = db.relationship('Person', secondary=teacher_class_table,
                                      backref='teaching_classes', lazy='dynamic')
    school_subjects = db.relationship('Subject', secondary=subject_class_table,
                                      backref='school_classes', lazy='dynamic')
    main_teacher_id = db.Column(db.Integer)


class SubjectType(db.Model):
    __tablename__ = 'subject_types'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    description = db.Column(db.String(50))


class Employee(db.Model):
    __tablename__ = 'employees'

    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String(50))
    person_id = db.Column(db.Integer, db.ForeignKey('persons.id'))
    person = db.relationship('Person', backref='roles')


class SchoolLessonJournal(db.Model):
    __tablename__ = 'school_lessons'

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date)
    grade_type = db.Column(db.String(50))
    grade = db.Column(db.Integer)
    lesson_comment = db.Column(db.String(120))
    school_class_id = db.Column(db.Integer, db.ForeignKey('school_classes.id'))
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'))

    student_id = db.Column(db.Integer, db.ForeignKey('persons.id'))
    lesson_id = db.Column(db.Integer, db.ForeignKey('lessons.id'))

    student = db.relationship('Person', backref='school_lessons')
    lesson = db.relationship('Lesson', backref='lesson_records')


class Report(db.Model):
    __tablename__ = 'reports'

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date)
    duty_type = db.Column(db.String(50))
    duty_hours = db.Column(db.Integer)

    person_id = db.Column(db.Integer, db.ForeignKey('persons.id'))
    person = db.relationship('Person', backref='reports')
