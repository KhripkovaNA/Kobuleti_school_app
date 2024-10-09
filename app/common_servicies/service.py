from datetime import datetime, timedelta
import pytz
from dateutil.relativedelta import relativedelta


DAYS_OF_WEEK = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
MONTHS = [
    "январь", "февраль", "март", "апрель", "май", "июнь", "июль",
    "август", "сентябрь", "октябрь", "ноябрь", "декабрь"
]
OPERATION_TYPES = {"cash": "нал", "bank": "счет", "balance": "депозит"}
OPERATION_CATEGORIES = {
    'after_school': 'Продленка', 'del_after_school': 'Продленка', 'subscription': 'Абонемент',
    'del_subscription': 'Абонемент', 'lesson': 'Занятие', 'del_lesson': 'Занятие',
    'balance': 'Депозит, пополнение/возврат', 'salary': 'Зарплата', 'dining': 'Питание',
    'school': 'Школа', 'stationery': 'Канцелярия', 'finance': 'Прочее', 'sublease': 'Аренда',
    'assessment': 'Аттестация', 'collection': 'Инкассация', 'household': 'Хозтовары'
}
CHILD = "Ребенок"
ADULT = "Взрослый"
TEACHER = "Учитель"
CHILD_SELF = "Сам ребенок"
CHOOSE = "Выбрать"
OTHER = "Другое"
LOCAL_TZ = pytz.timezone('Asia/Tbilisi')


def get_today_date():
    return datetime.now(LOCAL_TZ).date()


def get_period(month_index):
    result_date = get_today_date() + relativedelta(months=month_index)
    return result_date.month, result_date.year


def get_date(day_of_week, week=0):
    today = get_today_date()
    day_of_week_date = today - timedelta(days=today.weekday()) + timedelta(days=day_of_week) + week * timedelta(weeks=1)
    return day_of_week_date


def get_date_range(week):
    date_start = get_date(0, week)
    dates = [f"{date_start + timedelta(day):%d.%m}" for day in range(7)]
    return dates


def get_weekday_date(day_of_week, date=None):
    if date is None:
        date = get_today_date()
    date_of_week_day = date - timedelta(days=date.weekday()) + timedelta(days=day_of_week)
    return date_of_week_day


def get_week_dates():
    week_dates = [get_date(0), get_date(0, 1), get_date(0, -1)]
    return week_dates


def calc_month_index(date):
    date1 = date.replace(day=1)
    date2 = get_today_date().replace(day=1)

    return relativedelta(date1, date2).months


def calculate_week(date):
    return int((get_weekday_date(0, date) - get_weekday_date(0, get_today_date())).days / 7)


def conjugate_lessons(number):
    last_digit = number % 10
    last_two_digits = number % 100

    if 10 <= last_two_digits <= 20:
        return f"{number} занятий"
    elif last_digit == 1:
        return f"{number} занятие"
    elif 2 <= last_digit <= 4:
        return f"{number} занятия"
    else:
        return f"{number} занятий"


def conjugate_years(number):
    last_digit = number % 10
    last_two_digits = number % 100

    if 10 <= last_two_digits <= 20:
        return f"{number} лет"
    elif last_digit == 1:
        return f"{number} год"
    elif 2 <= last_digit <= 4:
        return f"{number} года"
    else:
        return f"{number} лет"


def conjugate_hours(number):
    last_digit = number % 10
    last_two_digits = number % 100

    if 10 <= last_two_digits <= 20:
        return f"{number} часов"
    elif last_digit == 1:
        return f"{number} час"
    elif 2 <= last_digit <= 4:
        return f"{number} часа"
    else:
        return f"{number} часов"


def conjugate_days(number):
    last_digit = number % 10
    last_two_digits = number % 100

    if 10 <= last_two_digits <= 20:
        return f"{number} дней"
    elif last_digit == 1:
        return f"{number} день"
    elif 2 <= last_digit <= 4:
        return f"{number} дня"
    else:
        return f"{number} дней"

