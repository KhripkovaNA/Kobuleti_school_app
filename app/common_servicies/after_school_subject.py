from app.school.subjects.models import Subject, SubjectType


def after_school_subject():
    after_school = Subject.query.filter(Subject.subject_type.has(SubjectType.name == 'after_school')).first()
    return after_school
