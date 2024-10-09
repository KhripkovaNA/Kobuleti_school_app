from app import db
from decimal import Decimal
from datetime import datetime, timedelta
from .models import Finance
from app.common_servicies.service import get_today_date
from app.app_settings.models import SubscriptionType
from app.school.models import Person
from app.school.subscriptions.models import Subscription


def finance_operation(person, amount, operation_type, description, service,
                      service_id=None, balance=False, subject_id=None, date=None):
    if not date:
        date = get_today_date()

    if balance:
        person.balance += Decimal(amount)
    elif operation_type == 'balance':
        person.balance += Decimal(amount)
        operation_type = None
        balance = True

    new_operation = Finance(
        person_id=person.id if person else None,
        date=date,
        amount=amount,
        operation_type=operation_type,
        student_balance=balance,
        description=description,
        service=service,
        service_id=service_id,
        balance_state=person.balance if person else None,
        subject_id=subject_id
    )
    db.session.add(new_operation)
    db.session.flush()


def purchase_subscription(form):
    student_id = int(form.get('student_id'))
    student = Person.query.filter_by(id=student_id, status="Клиент").first()
    subject_id = int(form.get('selected_subject'))
    subscription_type_id = int(form.get('subscription_type'))
    subscription_type = SubscriptionType.query.filter_by(id=subscription_type_id).first()
    purchase_date = datetime.strptime(form.get('purchase_date'), '%d.%m.%Y').date()
    end_date = purchase_date + timedelta(subscription_type.duration)
    operation_type = form.get('operation_type')

    new_subscription = Subscription(
        subject_id=subject_id,
        student_id=student.id,
        subscription_type_id=subscription_type_id,
        lessons_left=subscription_type.lessons,
        purchase_date=purchase_date,
        end_date=end_date
    )
    return new_subscription, subscription_type.price, operation_type
