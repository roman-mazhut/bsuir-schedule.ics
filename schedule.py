# -*- coding: utf-8 -*-
import re
import requests
from datetime import datetime, timedelta
from icalendar import Calendar, Event
import xml.etree.ElementTree as ET


DAYS_OF_WEEK_LIST = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресение']

DAYS_OF_WEEK = {
    'Понедельник': 'MO',
    'Вторник': 'TU',
    'Среда': 'WE',
    'Четверг': 'TH',
    'Пятница': 'FR',
    'Суббота': 'SA',
    'Воскресение': 'SU',
}


def get_group_id(group_number):
    groups_api_request = requests.get('http://www.bsuir.by/schedule/rest/studentGroup')
    groups = ET.fromstring(groups_api_request.text.encode('utf-8'))
    for group in groups:
        if group.find('name').text == str(group_number):
            return group.find('id').text

def get_xml_group_schedule(group_number):
    group_id = get_group_id(group_number)
    schedule_api_request = requests.get('http://www.bsuir.by/schedule/rest/schedule/%s/' % group_id)
    schedule = ET.fromstring(schedule_api_request.text.encode('utf-8'))
    return schedule

def get_week_number():
    request = requests.get('http://www.bsuir.by/schedule/schedule.xhtml')
    week_number_regexp = re.compile(r'<span class="week">.+(\d).+<\/span>')
    result = week_number_regexp.search(request.text)
    if result is not None:
        return int(result.group(1))


def build_ics(group_number, subgroup):
    calendar = Calendar()
    xml_schedule = get_xml_group_schedule(group_number)
    localtime = datetime.now()
    current_week = get_week_number()
    for day_of_week in xml_schedule:
        for lesson in day_of_week.findall('schedule'):
            if int(lesson.find('numSubgroup').text) not in [0, subgroup]:
                continue
            for week_number in lesson.findall('weekNumber'):
                if int(week_number.text) == 0:
                    continue
                event = Event()
                subject = lesson.find('subject').text
                auditory = lesson.find('auditory').text
                employee = lesson.find('employee')
                employee_first_name = employee.find('firstName').text
                employee_middle_name = employee.find('middleName').text
                employee_last_name = employee.find('lastName').text
                lesson_type = lesson.find('lessonType').text
                summary = "%s %s %s %s %s. %s." % (
                    lesson_type,
                    subject,
                    auditory,
                    employee_last_name,
                    employee_first_name[0],
                    employee_middle_name[0],
                )
                time_interval = lesson.find('lessonTime').text
                name_of_day_of_week = day_of_week.find('weekDay').text.encode('utf-8')
                # week number related to the current week
                delta_days = 7 * (int(week_number.text) - current_week)
                # day of week related to the current day
                delta_days += DAYS_OF_WEEK_LIST.index(name_of_day_of_week) - localtime.weekday()
                time_start, time_end = map(
                    lambda t: datetime.strptime(t, "%H:%M").replace(
                        year=localtime.year,
                        month=localtime.month,
                        day=localtime.day
                    ) + timedelta(days=delta_days),
                    time_interval.split('-')
                )
                event.add('summary', summary)
                event.add('dtstart', time_start)
                event.add('dtend', time_end)
                event.add('dtstamp', localtime)
                event.add('rrule', 'FREQ=WEEKLY;BYDAY=%s;INTERVAL=4' % (DAYS_OF_WEEK[name_of_day_of_week],), encode=False)

                calendar.add_component(event)


    f = open('cal.ics', 'wb')
    f.write(calendar.to_ical().replace('\\;', ';'))
    f.close()

def main():
    build_ics(110901, 2)

if __name__ == '__main__':
    main()
