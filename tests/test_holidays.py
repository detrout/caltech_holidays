from datetime import date, datetime
from lxml.html import parse, fromstring
from pathlib import Path
from unittest import TestCase

from caltech_holidays import (
    Calendar,
    get_calendar_entries,
    get_event_uid,
    get_known_event_uids,
    get_table_from_header,
    get_table_entries,
    get_year_from_header,
    add_unique_event,
    make_event,
)


class TestCaltechHolidays(TestCase):
    def setUp(self):
        testdata = Path(__file__).parent / "holiday-observances.html"
        with open(testdata, "rt") as instream:
            self.tree = parse(instream)

    def test_get_calendar_entries(self):
        count = 0
        for date, description in get_calendar_entries(self.tree):
            count += 1

        self.assertEqual(count, 30)

    def test_get_table_entries(self):
        testdata = ["<table><thead></thead><tbody>"]
        testdata.append("<tr><td>1</td><td>Monday</td><td>January 1</td><td>New Year's Day</td></tr>")
        testdata.append("<tr><td>2</td><td>Monday</td><td>January 15</td><td>Martin Luther King</td></tr>")
        testdata.append("</tbody></table>")
        tree = fromstring("\n".join(testdata))

        entries = list(get_table_entries("2024", tree))
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0].date, date(2024, 1, 1))
        self.assertEqual(entries[0].description, "New Year's Day")
        self.assertEqual(entries[1].date, date(2024, 1, 15))
        self.assertEqual(entries[1].description, "Martin Luther King")

    def test_get_table_personal_holiday(self):
        testdata = ["<table><thead></thead><tbody>"]
        testdata.append("<tr><td>13</td><td>-</td><td>-</td><td>Personal Holiday</td></tr>")
        testdata.append("</tbody></table>")
        tree = fromstring("\n".join(testdata))
        entries = list(get_table_entries("2024", tree))

        self.assertEqual(len(entries), 0)

    def test_get_year_from_header(self):
        testdata = "<h3>Caltech Holiday Observances for 2024</h3>"
        tree = fromstring(testdata)

        year = get_year_from_header(tree)
        self.assertEqual(year, "2024")
        
    def test_make_event(self):
        event1 = make_event(date(2024, 1, 1), "test_event", datetime(2023, 5, 1, 12, 34))
        event2 = make_event(date(2024, 1, 1), "test_event", datetime(2023, 10, 1, 12, 34))

        self.assertEqual(event1["SUMMARY"], "test_event")
        self.assertEqual(event1["DTSTART"].dt, date(2024, 1, 1))
        self.assertEqual(event1["DTEND"].dt, date(2024, 1, 2))
        self.assertEqual(event1["UID"], event2["UID"])

    def test_get_event_uid(self):
        event1 = make_event(date(2023, 1, 2), "New Year's Day", datetime(2022, 10, 1, 12, 34))
        event2 = Calendar.from_ical("""BEGIN:VEVENT
SUMMARY:New Year's Day
DTSTART;VALUE=DATE:20230102
DTEND;VALUE=DATE:20230103
DTSTAMP;VALUE=DATE-TIME:20230327T185843Z
UID:8f783bd2c4ac4ffdce7e352aac417eaed54237c58c1e1fb2d7d8b8f3a9e9dd3d
END:VEVENT
""")
        event1_uid = get_event_uid(event1)
        self.assertEqual(
            event1_uid, "66e129bf42e4046d912598b2a70e4e2f45beec14eb24a8ebb947fe2c80c5948b")

        event2_uid = get_event_uid(event2)
        self.assertEqual(event1_uid, event2_uid)
        
    def test_known_event_uids(self):
        event1 = make_event(date(2024, 1, 1), "test_event1", datetime(2023, 10, 1, 12, 34))
        event2 = make_event(date(2024, 1, 15), "test_event2", datetime(2023, 10, 1, 12, 34))
        event3 = make_event(date(2024, 1, 1), "test_event1", datetime(2023, 10, 1, 12, 34))

        cal = Calendar()
        cal.add_component(event1)
        cal.add_component(event2)

        uids = get_known_event_uids(cal)
        self.assertEqual(uids, set((
            "6a7547b3f94c71ce0f5458bbac92efdd98c39bb7e3bb2ffcf28da6dcd0076f1f",
            "771ed7592fc59d584934c0b8302d3c09cb7a3c9c2d3787bec86dbabfd7741bac",
        )))
        
    def test_merging_events(self):
        dtstamp = datetime(2023, 5, 1, 12, 34)
        event1 = make_event(date(2024, 1, 1), "test_event1", dtstamp)
        event2 = make_event(date(2024, 1, 15), "test_event2", dtstamp)
        event3 = make_event(date(2024, 1, 1), "test_event1", dtstamp)

        cal = Calendar()
        add_unique_event(cal, event1)
        self.assertEqual(len(cal.subcomponents), 1)

        add_unique_event(cal, event2)
        self.assertEqual(len(cal.subcomponents), 2)

        add_unique_event(cal, event3)
        self.assertEqual(len(cal.subcomponents), 2)
