#!/usr/bin/python3

import argparse
import sys
import hashlib
from icalendar import Calendar, Event
from datetime import datetime, timedelta
from lxml.html import parse
from urllib.request import urlopen
from urllib.error import HTTPError
import logging

LOGGER = logging.getLogger('Holidays')

ERROR_GET_PAGE_FAILED = 1
ERROR_PARSE_FAILED = 2
ERROR_NO_EVENTS = 3
ERROR_UNKNOWN = 255

def main(cmdline=None):
    parser = make_parser()
    args = parser.parse_args(cmdline)

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    elif args.verbose:
        logging.basicConfig(level=logging.INFO)
    else:
        logging.basicConfig(level=logging.WARN)

    request = request_holiday_page()
    if request is None:
        LOGGER.error("Downloading holiday page failed")
        return ERROR_GET_PAGE_FAILED

    dtstamp = parse_last_modified(request.headers['Last-Modified'])
    if dtstamp is None:
        LOGGER.error('No Last-Modified header')
        return ERROR_PARSE_FAILED

    tree = parse(request)

    cal = Calendar()
    cal.add('version', '2.0')
    cal.add('prodid', 'ghic.org:caltech_holiday.py')

    event_count = 0
    for date, description in get_calendar_entries(tree):
        event_count += 1
        cal.add_component(make_event(date, description, dtstamp))

    if args.icalendar:
        with open(args.icalendar, 'wb') as outstream:
            outstream.write(cal.to_ical())

    if args.display:
        print(display(cal).decode('utf-8'))

    if event_count == 0:
        LOGGER.warn('No entries found')
        return ERROR_NO_EVENTS

    return 0


def request_holiday_page():
    ical_url = 'https://hr.caltech.edu/perks/time_away/holiday_observances'
    request = urlopen(ical_url)
    if request.status != 200:
        LOGGER.error('Error opening page: {}'.format(request.status))
        return None

    return request


def get_calendar_entries(tree):
    headers = tree.xpath('//h3')
    LOGGER.debug('Found {} header tags'.format(len(headers)))
    for h in headers:
        year = get_year_from_header(h)
        LOGGER.debug('year: %s', year)
        if year is None:
            continue

        table = get_table_from_header(h)
        yield from get_table_entries(year, table)


def get_year_from_header(header):
    header = header.text_content().strip()
    if not header.startswith('Caltech Holiday Observances for '):
        LOGGER.error('Unrecognized table title: %s', header)
        return None

    return header[-4:]


def get_table_from_header(header):
    section = header.getparent()
    node = section.getnext()
    while node is not None:
        if node.attrib.get('class') == 'block-TableBlock':
            tables = node.xpath('*/table')
            assert len(tables) == 1, 'page layout changed'
            return tables[0]
        node = node.getnext()


def get_table_entries(year, table):
    for row in table.xpath('tbody/tr'):
        record = row.getchildren()
        if len(record) == 4:
            day = record[2].text_content().strip()
            LOGGER.debug('day: %s', day)
            if not day.startswith('-'):
                description = record[3].text_content().strip()
                LOGGER.debug('description: %s', description)
                try:
                    # in case there's an overriden year
                    date = datetime.strptime(day, "%B %d, %Y").date()
                except ValueError:
                    date = datetime.strptime(year + ' ' + day, '%Y %B %d').date()
                yield (date, description)
            else:
                LOGGER.info('unrecognized calendar line: {}'.format(row.text_content))


def make_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('--icalendar', default='caltech_holidays.ics',
                        help='Name to write icalendar file to')
    parser.add_argument('--display', default=False, action='store_true',
                        help='Print calendar')
    parser.add_argument('-v', '--verbose', default=False, action='store_true',
                        help='enable INFO level log messages')
    parser.add_argument('-vv', '--debug', default=False, action='store_true',
                        help='enable DEBUG level log messages')
    return parser


def display(cal):
    return cal.to_ical().replace(b'\r\n', b'\n').strip()


def parse_last_modified(header):
    if header is None:
        return datetime.now()

    return datetime.strptime(header, '%a, %d %b %Y %H:%M:%S %Z')


def make_event(event_date, description, dtstamp):
    event = Event()
    tomorrow = event_date + timedelta(days=1)
    body = event_date.isoformat() + dtstamp.isoformat() + description
    uid = hashlib.sha256(body.encode('utf-8'))
    event.add('uid', uid.hexdigest())
    event.add('dtstart', event_date)
    event.add('dtend', tomorrow)
    event.add('dtstamp', dtstamp)
    event.add('summary', description)
    return event


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        LOGGER.error("Unexpected error: {}".format(e))
        sys.exit(ERROR_UNKNOWN)
