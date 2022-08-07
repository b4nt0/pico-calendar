from epaper import Screen
import time


class DateUtil:
    months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
    days_of_week = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    
    @staticmethod
    def date_to_iso(dt_tuple):
        return '{year:02d}-{month:02d}-{day:02d}'.format(year=dt_tuple[0], month=dt_tuple[1], day=dt_tuple[2])
    
    @staticmethod
    def add_days(dt_tuple, days=1):
        dt_seconds = time.mktime(dt_tuple)
        dt_seconds += days * 60 * 60 * 24
        return time.localtime(dt_seconds)
    
    @staticmethod
    def iso_to_date(iso_string):
        just_date = iso_string.split('T')[0]
        date_components = just_date.split('-')
        dt_seconds = time.mktime((int(date_components[0]), int(date_components[1]), int(date_components[2]), 12, 00, 0, 0, 0))
        dt = time.localtime(dt_seconds)
        return dt
    
    @staticmethod
    def date_to_nice(dt_tuple):
        return '{dow}, the {day} of {month}'.format(
            dow=DateUtil.days_of_week[dt_tuple[6]],
            day=dt_tuple[2],
            month=DateUtil.months[dt_tuple[1]-1])
        
    @staticmethod
    def iso_to_nice(iso_string):
        dt = DateUtil.iso_to_date(iso_string)
        return DateUtil.date_to_nice(dt)


class Calendar:
    LETTER_HEIGHT = 20
    LETTER_WIDTH = 13
    
    def __init__(self, screen):
        self.screen = screen

    def draw_calendar(self, dt_tuple):
        # Year is 4 digits, e.g. 2022
        # Month is 1-12
        # Mday is 1-31
        # Weekday is 0-6 for Mon-Sun
        year = dt_tuple[0]
        month = dt_tuple[1]
        mday = dt_tuple[2]
        weekday = dt_tuple[6]
        
        self.screen.text_sans(str(year), 5, self.screen.x_middle - Calendar.LETTER_WIDTH * 2)
        
        months = DateUtil.months
        days_in_months = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        self.screen.text_courier(months[month - 1], 35, int(self.screen.x_middle - Calendar.LETTER_WIDTH * len(months[month - 1]) / 2))
        
        week_excess_from_1st = (mday - 1) % 7
        weekday_1st = (weekday - week_excess_from_1st + 7) % 7
        
        day_col_width_px = Calendar.LETTER_WIDTH * 3
        first_day_col_start_px = int(self.screen.x_middle - day_col_width_px * 7 / 2)
        first_day_row_start_px = 70
        
        day_row = 1
        day = 1
        days = days_in_months[month - 1]
        wday = weekday_1st
        if month == 2:
            # Check for leap year
            if year % 400 == 0:
                days = 29
            elif year % 100 == 0:
                pass
            elif year % 4 == 0:
                days = 29
        
        while day <= days:
            day_str = str(day)
            if len(day_str) == 1: day_str = ' ' + day_str
            self.screen.text_courier(day_str,
                                     first_day_row_start_px + Calendar.LETTER_HEIGHT * day_row, first_day_col_start_px + wday * day_col_width_px,
                                     red=(wday in [5,6]),
                                     inverse=(day == mday))
            
            day += 1
            wday += 1
            if wday > 6:
                wday = 0
                day_row += 1
