from app import db
from datetime import datetime
from app.app_settings.service import user_action
from app.common_servicies.service import (
    ADULT, CHOOSE, OTHER, CHILD_SELF, CHILD, MONTHS, get_today_date, conjugate_years
)
from app.finance.models import Finance
from app.finance.service import finance_operation
from app.school.employees.models import Employee
from app.school.models import Person, Contact, parent_child_table
from app.school.subjects.models import Subject, SubjectType
from app.school.subscriptions.models import Subscription
from app.school.subscriptions.service import check_subscription
from app.school_classes.models import SchoolClass


def person_age(dob):
    today = get_today_date()
    age = get_today_date().year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    return conjugate_years(age)


def format_status(student):
    if student.status == "Закрыт":
        student.status_info = f"{student.status} причина: {student.leaving_reason}"
    elif student.status == "Пауза":
        student.status_info = f"{student.status} до {student.pause_date}" if student.pause_date else student.status
    else:
        student.status_info = student.status


def format_children(person):
    children = []
    for child in person.children.all():
        child_age = person_age(child.dob) if child.dob else None
        child_info = f'{child.last_name} {child.first_name} ({child_age})' \
            if child_age else f'{child.last_name} {child.first_name}'
        children.append((child.id, child_info))
    person.children_info = children


def format_student_info(student):
    if student.dob:
        dob = student.dob
        student.birth_date = f'{dob:%d.%m.%Y}'
        student.age = person_age(dob)
    if student.pause_until:
        student.pause_date = f'{student.pause_until:%d.%m.%y}'

    format_status(student)

    if student.balance > 0:
        student.balance_plus = round(student.balance, 1)
    elif student.balance < 0:
        student.balance_minus = round(student.balance, 1)
    if student.children.all():
        format_children(student)
    if student.roles:
        student.employee_roles = ', '.join([role.role for role in student.roles])


def format_main_contact(student):
    main_contact = Person.query.filter_by(id=student.primary_contact).first()
    if main_contact.contacts[0].telegram:
        student.contact = f"Телеграм: {main_contact.contacts[0].telegram}"
    elif main_contact.contacts[0].phone:
        student.contact = f"Тел.: {main_contact.contacts[0].phone}"
    elif main_contact.contacts[0].other_contact:
        student.contact = main_contact.contacts[0].other_contact

    if main_contact.id != student.id:
        contact_type = db.session.query(parent_child_table.c.relation).filter(
            parent_child_table.c.parent_id == main_contact.id,
            parent_child_table.c.child_id == student.id).scalar()
        student.contact_name = f"{contact_type} - {main_contact.last_name} {main_contact.first_name}"


def basic_student_info(student):
    format_student_info(student)
    format_main_contact(student)


def format_all_contacts(student):
    contacts = []

    if student.contacts:
        if student.primary_contact == student.id:
            student.main_contact = student
            student.main_contact.type = CHILD_SELF
        else:
            student.type = CHILD_SELF
            contacts.append(student)

    for parent in student.parents.all():
        parent.type = db.session.query(parent_child_table.c.relation).filter(
            parent_child_table.c.parent_id == parent.id,
            parent_child_table.c.child_id == student.id).scalar()
        if student.primary_contact == parent.id:
            student.main_contact = parent
        else:
            contacts.append(parent)

    student.additional_contacts = contacts


def format_subjects_and_subscriptions(student):
    check_subscription(student, 0, 0)
    subscriptions = []
    subscriptions_list = []
    subscriptions_set = set()
    after_school_list = []

    school = [student.school_class.school_name] if student.school_class else []

    for subscription in student.subscriptions:
        subject = subscription.subject
        is_after_school = subscription.is_after_school
        is_active = subscription.active
        subscription_dict = {}

        if is_active and not is_after_school:
            subscription_dict['subscription_id'] = subscription.id
            subscription_dict['subject_name'] = subject.name
            subscription_dict['lessons_left'] = subscription.lessons_left
            subscription_dict['purchase_date'] = f'{subscription.purchase_date:%d.%m.%Y}'
            subscription_dict['end_date'] = f'{subscription.end_date:%d.%m.%Y}'
            subscription_dict['full_subscription'] = True \
                if subscription.lessons_left == subscription.subscription_type.lessons else False
            subscriptions.append(subscription_dict)
            subscriptions_list.append(f'{subject.name}({subscription.lessons_left})')
            subscriptions_set.add(subject.id)

        elif is_after_school:
            if is_active:
                subscription_dict['subscription_id'] = subscription.id
                subscription_dict['purchase_date'] = subscription.purchase_date
                subscription_dict['shift'] = subscription.shift
                if subscription.period == "month":
                    subscription_dict['period'] = "месяц"
                    subscription_dict['validity'] = MONTHS[subscription.purchase_date.month - 1]
                elif subscription.period == "week":
                    subscription_dict['period'] = "неделя"
                    subscription_dict['validity'] = f'{subscription.purchase_date:%d.%m}-' \
                                                    f'{subscription.end_date:%d.%m.%y}'
                after_school_list.append(subscription_dict)
                subscriptions_list.insert(0, f'{subject.name} ({subscription_dict["validity"]})')
                subscriptions_set.add(subject.id)
            else:
                day_delta = (subscription.purchase_date - get_today_date()).days
                if (-30 <= day_delta <= 30) and subscription.period != "month":
                    subscription_dict['subscription_id'] = subscription.id
                    subscription_dict['purchase_date'] = subscription.purchase_date
                    subscription_dict['shift'] = subscription.shift
                    subscription_dict['period'] = "день" if subscription.period == "day" else "неделя" \
                        if subscription.period == "week" else subscription.period
                    subscription_dict['validity'] = f'{subscription.purchase_date:%d.%m}-' \
                                                    f'{subscription.end_date:%d.%m.%y}' \
                        if subscription.period == "week" else f'{subscription.purchase_date:%d.%m}'

                    after_school_list.append(subscription_dict)
                    subscriptions_set.add(subject.id)

    all_subjects_list = sorted(
        [(subject.name, subject.id) for subject in student.subjects if subject.subject_type.name != "school"])
    extra_subjects = sorted([subject.name for subject in student.subjects if
                             subject.id not in subscriptions_set and subject.subject_type.name != "school"])

    student.extra_subjects = extra_subjects
    student.subjects_info = ', '.join(school + subscriptions_list + extra_subjects)
    student.subscriptions_info = subscriptions
    student.after_school_info = after_school_list
    student.all_subjects = ([(school[0], 0)] if school else []) + all_subjects_list


def extensive_student_info(student):
    format_student_info(student)
    format_all_contacts(student)
    format_subjects_and_subscriptions(student)


def clients_data(person_type):
    if person_type == 'child':
        all_clients = Person.query.filter(
            Person.contacts.any(~Contact.id.is_(None))
        ).order_by(Person.last_name, Person.first_name).all()
    elif person_type == 'adult':
        all_clients = Person.query.filter(Person.status.is_(None)).order_by(Person.last_name, Person.first_name).all()
    else:
        all_clients = Person.query.filter(
            ~Person.roles.any(Employee.id),
            Person.person_type == ADULT
        ).order_by(Person.last_name, Person.first_name).all()
    clients = []
    for client in all_clients:
        client_data = {
            "id": client.id,
            "last_name": client.last_name,
            "first_name": client.first_name,
            "patronym": client.patronym
        }
        if client.contacts:
            client_data["telegram"] = client.contacts[0].telegram
            client_data["phone"] = client.contacts[0].phone
            client_data["other_contact"] = client.contacts[0].other_contact
        else:
            client_data["telegram"] = ""
            client_data["phone"] = ""
            client_data["other_contact"] = ""

        clients.append(client_data)

    return clients


def create_student(form, student_type):
    last_name = form.last_name.data
    first_name = form.first_name.data
    patronym = form.patronym.data
    status = form.status.data
    same_person = Person.query.filter_by(last_name=last_name, first_name=first_name).all()
    if not same_person:
        if student_type == 'child':
            dob = datetime.strptime(form.dob.data, '%d.%m.%Y').date() \
                if form.dob.data else None
            person_type = CHILD

        else:
            dob = None
            person_type = ADULT

        student = Person(
            last_name=last_name,
            first_name=first_name,
            patronym=patronym,
            dob=dob,
            person_type=person_type,
            status=status
        )
        message = ''

    else:
        student = None
        message = f"Человек с именем {last_name} {first_name} уже есть в системе"

    return student, message


def create_contact(form):
    telegram = form.telegram.data
    phone = form.phone.data
    other_contact = form.other_contact.data

    contact = Contact(
        telegram=telegram,
        phone=phone,
        other_contact=other_contact
    )

    return contact


def create_parent(contact_form):
    parent_last_name = contact_form.parent_last_name.data
    parent_first_name = contact_form.parent_first_name.data
    parent_patronym = contact_form.parent_patronym.data
    same_person = Person.query.filter_by(last_name=parent_last_name, first_name=parent_first_name).all()

    if not same_person:
        parent = Person(
            last_name=parent_last_name,
            first_name=parent_first_name,
            patronym=parent_patronym,
            person_type=ADULT
        )
        message = ''

    else:
        parent = None
        message = f"Человек с именем {parent_last_name} {parent_first_name} уже есть в системе"

    return parent, message


def handle_contact_info(contact_form, student):
    contact_select = contact_form.contact_select.data
    relation_type = contact_form.relation.data
    student_contacts = Contact.query.filter_by(person_id=student.id).first()
    if relation_type == CHILD_SELF:
        if not student_contacts:
            contact = create_contact(contact_form)
            db.session.add(contact)
            db.session.flush()
            student.contacts.append(contact)

        else:
            contact = student.contacts[0]
            student.contacts[0].telegram = contact_form.telegram.data
            student.contacts[0].phone = contact_form.phone.data
            student.contacts[0].other_contact = contact_form.other_contact.data

        db.session.flush()

    else:
        if contact_select == CHOOSE:
            parent_id = int(contact_form.selected_contact.data)
            parent = Person.query.filter_by(id=parent_id).first()
            contact = Contact.query.filter_by(person_id=parent_id).first()

        else:
            parent, message = create_parent(contact_form)
            if parent:
                contact = create_contact(contact_form)
                db.session.add(parent)
                db.session.add(contact)
                db.session.flush()

                parent.contacts.append(contact)
                parent.primary_contact = parent.id

            else:
                return message

        student.parents.append(parent)
        db.session.flush()
        assign_relation_type(contact_form, student, parent)

    if contact_form.primary_contact.data:
        student.primary_contact = contact.person_id

    return ''


def assign_relation_type(form, student, parent):
    relation_type = form.relation.data

    if relation_type == OTHER:
        relation_type = form.other_relation.data

    relation_entry = parent_child_table.update().where(
        (parent_child_table.c.parent_id == parent.id) &
        (parent_child_table.c.child_id == student.id)
    ).values(relation=relation_type)

    db.session.execute(relation_entry)


def add_child(form):
    student, message = create_student(form, 'child')
    if student:
        db.session.add(student)
        db.session.flush()

        for contact_form in form.contacts:
            message = handle_contact_info(contact_form, student)
            if message:
                return None, message

    return student, message


def add_adult(form):
    client_select = form.client_select.data
    if client_select == CHOOSE:
        client_id = int(form.selected_client.data)
        client = Person.query.filter_by(id=client_id).first()
        client.status = form.status.data
        message = ''
        db.session.flush()

    else:
        client, message = create_student(form, 'adult')
        if client:
            contact = create_contact(form)
            db.session.add(client)
            db.session.add(contact)
            db.session.flush()
            client.contacts.append(contact)
            client.primary_contact = client.id
            db.session.flush()

    return client, message


def potential_client_subjects():
    school_classes = SchoolClass.query.order_by(SchoolClass.school_name).all()
    potential_classes = [(school_class.id, school_class.school_name) for school_class in school_classes
                         if school_class.school_name.endswith("класс")]
    all_subjects = Subject.query.filter(
        Subject.subject_type.has(SubjectType.name.in_(["extra", "after_school", "individual"]))
    ).order_by(Subject.name).all()
    potential_subjects = [(subject.id, f"{subject.name} ({subject.subject_type.description})")
                          for subject in all_subjects]

    return {"school": potential_classes, "subjects": potential_subjects}


def handle_student_edit(form, student, edit_type, user):
    if edit_type == 'edit_student':
        last_name = form.last_name.data
        first_name = form.first_name.data
        same_person = Person.query.filter(
            Person.id != student.id,
            Person.last_name == last_name,
            Person.first_name == first_name
        ).all()
        if same_person:
            return f"Человек с именем {last_name} {first_name} уже есть в системе"

        else:
            student.last_name = last_name
            student.first_name = first_name
            student.patronym = form.patronym.data
            student.dob = datetime.strptime(form.dob.data, '%d.%m.%Y').date() \
                if form.dob.data else None
            status = form.status.data
            if student.status != status and user.rights == 'admin':
                student.status = status
                if student.status == "Закрыт":
                    student.subjects = []
                    student.subscriptions = []
                student.pause_date = datetime.strptime(form.pause_until.data, '%d.%m.%Y').date() \
                    if form.pause_until.data and student.status == "Пауза" else None

                student.leaving_reason = form.leaving_reason.data if student.status == "Закрыт" else ''
            db.session.flush()

        return ''

    if edit_type == 'edit_main_contact':
        main_contact = student.main_contact
        if main_contact.id != student.id:
            contact_last_name = form.last_name.data
            contact_first_name = form.first_name.data
            same_person = Person.query.filter(
                Person.id != main_contact.id,
                Person.last_name == contact_last_name,
                Person.first_name == contact_first_name
            ).all()
            if same_person:
                return f"Человек с именем {contact_last_name} {contact_first_name} уже есть в системе"

            main_contact.last_name = contact_last_name
            main_contact.first_name = contact_first_name
            main_contact.patronym = form.patronym.data

        main_contact.contacts[0].telegram = form.telegram.data
        main_contact.contacts[0].phone = form.phone.data
        main_contact.contacts[0].other_contact = form.other_contact.data

        db.session.flush()
        return ''

    if edit_type.startswith('edit_contact_'):
        ind = int(edit_type[len('edit_contact_'):])
        contact = student.additional_contacts[ind - 1]
        if contact.id != student.id:
            contact_last_name = form.last_name.data
            contact_first_name = form.first_name.data
            same_person = Person.query.filter(
                Person.id != contact.id,
                Person.last_name == contact_last_name,
                Person.first_name == contact_first_name
            ).all()
            if same_person:
                return f"Человек с именем {contact_last_name} {contact_first_name} уже есть в системе"

            contact.last_name = contact_last_name
            contact.first_name = contact_first_name
            contact.patronym = form.patronym.data

        contact.contacts[0].telegram = form.telegram.data
        contact.contacts[0].phone = form.phone.data
        contact.contacts[0].other_conta = form.other_contact.data

        if form.primary_contact.data:
            student.primary_contact = contact.id
        db.session.flush()
        return ''

    if edit_type == 'new_contact':
        message = handle_contact_info(form, student)
        return message

    if edit_type == 'del_subject':
        del_subject_id = int(form.get('del_subject_btn'))
        if student.status == "Лид" and del_subject_id == 0:
            student.school_class_id = None
            db.session.flush()
        else:
            del_subject = Subject.query.filter_by(id=del_subject_id).first()
            if del_subject in student.subjects:
                student.subjects.remove(del_subject)
                db.session.flush()
        return ''

    if edit_type == 'subscription':
        for subscription_form in form.subscriptions:
            subscription_id = int(subscription_form.subscription_id.data)
            subscription = Subscription.query.filter_by(id=subscription_id).first()
            lessons_left = subscription_form.lessons.data
            purchase_date = datetime.strptime(subscription_form.purchase_date.data, '%d.%m.%Y').date()
            end_date = datetime.strptime(subscription_form.end_date.data, '%d.%m.%Y').date()
            if subscription.lessons_left != lessons_left or subscription.purchase_date != purchase_date \
                    or subscription.end_date != end_date:
                subscription.lessons_left = lessons_left
                subscription.purchase_date = purchase_date
                subscription.end_date = end_date
                description = f"Изменение абонемента {subscription.subject.name} клиента " \
                              f"{student.last_name} {student.first_name}"
                user_action(user, description)
        db.session.flush()
        return

    if edit_type == 'del_after_school':
        del_after_school_id = int(form.get('del_after_school'))
        del_after_school = Subscription.query.filter_by(id=del_after_school_id).first()
        if del_after_school:
            price = del_after_school.subscription_type.price
            if del_after_school.period not in ["month", "day", "week"]:
                hours = int(del_after_school.period.split()[0])
                price *= hours
            record = Finance.query.filter(
                Finance.person_id == del_after_school.student_id,
                Finance.service == "after_school",
                Finance.service_id == del_after_school.id
            ).first()
            if record:
                description = "Возврат за продленку"
                finance_operation(del_after_school.student, abs(record.amount), record.operation_type,
                                  description, "del_after_school", None, balance=record.student_balance)
                record.service_id = None
            else:
                description = "Возврат за продленку"
                finance_operation(del_after_school.student, price, 'cash', description,
                                  "del_after_school", del_after_school.id)
            db.session.delete(del_after_school)
            db.session.flush()

        return
