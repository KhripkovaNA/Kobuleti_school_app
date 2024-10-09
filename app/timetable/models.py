from app import db
from app.school_classes.models import class_lesson_table


student_lesson_registered_table = db.Table(
    'student_lesson_registered_table',
    db.Column('student_id', db.Integer, db.ForeignKey('persons.id')),
    db.Column('lesson_id', db.Integer, db.ForeignKey('lessons.id'))
)


class Lesson(db.Model):
    __tablename__ = 'lessons'

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date)
    start_time = db.Column(db.Time)
    end_time = db.Column(db.Time)
    lesson_completed = db.Column(db.Boolean, default=False)
    lesson_topic = db.Column(db.String(120), default="")
    lesson_comment = db.Column(db.String(200), default="")

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

    split_classes = db.Column(db.Boolean, default=False)

    students_registered = db.relationship('Person', secondary=student_lesson_registered_table,
                                          backref='lessons_registered', lazy='dynamic')


class StudentAttendance(db.Model):
    __tablename__ = 'student_attendances'

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date)
    lesson_time = db.Column(db.Time)
    payment_method = db.Column(db.String(50))
    price_paid = db.Column(db.Numeric(8, 3))
    subscription_lessons = db.Column(db.Integer)
    subscription_id = db.Column(db.Integer)

    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'))
    student_id = db.Column(db.Integer, db.ForeignKey('persons.id'))
    lesson_id = db.Column(db.Integer, db.ForeignKey('lessons.id'))
    attending_status = db.Column(db.String(50))

    subject = db.relationship('Subject', backref='completed_lessons')
    student = db.relationship('Person', backref='lessons_attended')
    lesson = db.relationship('Lesson', backref='students_attended')