import calendar


class TailwindCalendar(calendar.HTMLCalendar):
    cssclasses = [style + " text-3xl p-2" for style in calendar.HTMLCalendar.cssclasses]
    cssclass_month_head = "text-4xl month-head"
    cssclass_month = "text-center month"
    cssclass_year = "text-red-500 lead"


def generate_html_calendar(year, month):
    cal = TailwindCalendar()
    html_calendar = cal.formatmonth(year, month)

    return html_calendar
