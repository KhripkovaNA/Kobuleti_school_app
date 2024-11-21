def get_sidebar_data_dict(cache):
    if hasattr(cache.cache, '_cache'):
        cache_keys = list(cache.cache._cache.keys())
        with open('cache.txt', "a", encoding='utf-8') as file:
            file.write(', '.join(cache_keys) + '\n')

    classes_school = cache.get('classes_school')
    school_subjects = cache.get('school_subjects')
    school_attending_students = cache.get('school_attending_students')

    if classes_school is None:
        from app.school_classes.models import SchoolClass

        classes_school = SchoolClass.query.order_by(
            SchoolClass.school_class,
            SchoolClass.school_name
        ).all()

        cache.set('classes_school', classes_school)

    if school_subjects is None:
        from app.school.subjects.models import Subject
        from app.school.subjects.models import SubjectType

        school_subjects = Subject.query.filter(
            Subject.subject_type.has(SubjectType.name == "school")
        ).order_by(Subject.name).all()

        cache.set('school_subjects', school_subjects)

    if school_attending_students is None:
        from app.school.models import Person

        school_attending_students = Person.query.filter(
            Person.status == "Клиент",
            Person.school_class_id.is_not(None)
        ).order_by(Person.last_name, Person.first_name).all()

        cache.set('school_attending_students', school_attending_students)

    return dict(school_subjects=school_subjects,
                classes_school=classes_school,
                school_attending_students=school_attending_students)
