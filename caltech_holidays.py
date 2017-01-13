#!/usr/bin/python3

import sys
import hashlib
from icalendar import Calendar, Event
from datetime import datetime, timedelta
from lxml.html import parse
from urllib.request import urlopen

def main():
    ical_url = 'https://hr.caltech.edu/perks/time_away/holiday_observances'
    request = urlopen(ical_url)
    if request.status != 200:
        print('Error opening page: {}'.format(request.status))
        return 1

    dtstamp = parse_last_modified(request.headers['Last-Modified'])
    tree = parse(request)

    tables = tree.xpath('//section[@id="main"]/table')
    cal = Calendar()
    cal.add('version', '2.0')
    cal.add('prodid', 'ghic.org/caltech_holiday.py')
    
    for t in tables:
        p = t.getprevious()
        header = p.xpath('strong/span')[0].text
        assert header.startswith('Caltech Holiday Observances for ')
        year = header[-4:]
        for row in t.xpath('tbody/tr'):
            record = row.getchildren()
            day = record[2].text
            if day != '--':
                description = record[3].text
                date = datetime.strptime(year + ' ' + day, '%Y %B %d').date()

                cal.add_component(make_event(date, description, dtstamp))

    with open('caltech_holidays.ics', 'wb') as outstream:
        outstream.write(cal.to_ical())
        
    return 0

def display(cal):
    return cal.to_ical().replace(b'\r\n', b'\n').strip()

def parse_last_modified(header):
    if header is None:
        return datetime.now()

    return datetime.strptime(header, '%a, %d %b %Y %H:%M:%S %Z')

def make_event(date, description, dtstamp):
    event = Event()
    tomorrow = date + timedelta(days=1)
    body = date.isoformat() + dtstamp.isoformat() + description
    uid = hashlib.sha256(body.encode('utf-8'))
    event.add('uid', uid.hexdigest())
    event.add('dtstart', date)
    event.add('dtend', tomorrow)
    event.add('dtstamp', dtstamp)
    event.add('summary', description)
    return event

    

if __name__ == '__main__':
    sys.exit(main())
        
