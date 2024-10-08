from app import db
from decimal import Decimal
from .models import Finance
from ..common_servicies.service import get_today_date


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
