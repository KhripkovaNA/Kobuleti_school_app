from datetime import datetime, timedelta
import pytz
from dateutil.relativedelta import relativedelta


DAYS_OF_WEEK = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
MONTHS = ["январь", "февраль", "март", "апрель", "май", "июнь", "июль",
          "август", "сентябрь", "октябрь", "ноябрь", "декабрь"]
OPERATION_TYPES = {"cash": "нал", "bank": "счет", "balance": "депозит"}
OPERATION_CATEGORIES = {'after_school': 'Продленка', 'del_after_school': 'Продленка', 'subscription': 'Абонемент',
                        'del_subscription': 'Абонемент', 'lesson': 'Занятие', 'del_lesson': 'Занятие',
                        'balance': 'Депозит, пополнение/возврат', 'salary': 'Зарплата', 'dining': 'Питание',
                        'school': 'Школа',
                        'stationery': 'Канцелярия', 'finance': 'Прочее', 'sublease': 'Аренда',
                        'assessment': 'Аттестация', 'collection': 'Инкассация', 'household': 'Хозтовары'}
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