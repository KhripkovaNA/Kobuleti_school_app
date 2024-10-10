from app import db


class_lesson_table = db.Table(
    'class_lesson_table',
    db.Column('class_id', db.Integer, db.ForeignKey('school_classes.id')),
    db.Column('lesson_id', db.Integer, db.ForeignKey('lessons.id'))
)

teacher_class_table = db.Table(
    'teacher_class_table',
    db.Column('class_id', db.Integer, db.ForeignKey('school_classes.id')),
    db.Column('teacher_id', db.Integer, db.ForeignKey('persons.id'))
)

subject_class_table = db.Table(
    'subject_class_table',
    db.Column('class_id', db.Integer, db.ForeignKey('school_classes.id')),
    db.Column('subject_id', db.Integer, db.ForeignKey('subjects.id'))
)


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


class SchoolLessonJournal(db.Model):
    __tablename__ = 'school_lessons'

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date)
    grade_type = db.Column(db.String(50), default="")
    final_grade = db.Column(db.Boolean, default=False)
    grade = db.Column(db.Integer)
    lesson_comment = db.Column(db.String(120), default='')
    school_class_id = db.Column(db.Integer, db.ForeignKey('school_classes.id'))
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'))

    student_id = db.Column(db.Integer, db.ForeignKey('persons.id'))
    lesson_id = db.Column(db.Integer, db.ForeignKey('lessons.id'))

    student = db.relationship('Person', backref='school_lessons')
    lesson = db.relationship('Lesson', backref='lesson_records')
    subject = db.relationship('Subject', backref='lesson_records')
