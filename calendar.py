from epaper import Screen
import time


class DateUtil:
    months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
    days_of_week = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    days_in_months = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    
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
    
    @staticmethod
    def dates_equal(dt1, dt2):
        return dt1[0] == dt2[0] and dt1[1] == dt2[1] and dt1[2] == dt2[2]


class Calendar:
    LETTER_HEIGHT = 20
    LETTER_WIDTH = 13
    
    def __init__(self, screen, today_dt_tuple):
        self.screen = screen
        self.today = today_dt_tuple
        
        # Announcements
        self.announce_gs_today = False
        self.announce_gs_tomorrow = False
        self.announce_precip_today = None
        self.announce_precip_tomorrow = None
        
        # Initialize coordinate variables
        # Year is 4 digits, e.g. 2022
        # Month is 1-12
        # Mday is 1-31
        # Weekday is 0-6 for Mon-Sun
        self.year = self.today[0]
        self.month = self.today[1]
        self.mday = self.today[2]
        self.weekday = self.today[6]
        
        self.day_coordinates = []
        
        week_excess_from_1st = (self.mday - 1) % 7
        self.weekday_1st = (self.weekday - week_excess_from_1st + 7) % 7
        
        day_col_width_px = Calendar.LETTER_WIDTH * 3
        first_day_col_start_px = int(self.screen.x_middle - day_col_width_px * 7 / 2)
        first_day_row_start_px = 70
        
        self.left_border_px = first_day_col_start_px
        
        self.days = DateUtil.days_in_months[self.month - 1]
        wday = self.weekday_1st
        if self.month == 2:
            # Check for leap year
            if self.year % 400 == 0:
                self.days = 29
            elif self.year % 100 == 0:
                pass
            elif self.year % 4 == 0:
                self.days = 29
        
        day_row = 1
        day = 1
        while day <= self.days:
            self.day_coordinates.append((first_day_row_start_px + Calendar.LETTER_HEIGHT * day_row, first_day_col_start_px + wday * day_col_width_px))
            
            day += 1
            wday += 1
            if wday > 6:
                wday = 0
                day_row += 1
        
        
    def draw_garbage(self, garbage_schedule):
        tomorrow = DateUtil.add_days(self.today)
        self.screen.text('Garbage schedule', 10, 5)

        if len(garbage_schedule) == 0:
            self.screen.text('Nothing planned!', 12, 5)
            
        else:
            print_row = 12
            self.announce_gs_today = False
            self.announce_gs_tomorrow = False
            for item in garbage_schedule:
                _td = DateUtil.dates_equal(item['date'], self.today)
                _tm = DateUtil.dates_equal(item['date'], tomorrow)
                self.announce_gs_today = self.announce_gs_today or _td
                self.announce_gs_tomorrow = self.announce_gs_tomorrow or _tm
                
                red = _td or _tm
                self.screen.text(item['date_format'], print_row, 5, red)
                self.screen.text(item['type'], print_row + 1, 5, red)
                
                if item['date'][1] == self.month:
                    coordinate = self.day_coordinates[item['date'][2] - 1]
                    self.screen.imagered.hline(coordinate[1], coordinate[0] + Calendar.LETTER_HEIGHT - 2, Calendar.LETTER_WIDTH * 2, 0xff)
                    self.screen.imagered.hline(coordinate[1], coordinate[0] + Calendar.LETTER_HEIGHT - 1, Calendar.LETTER_WIDTH * 2, 0xff)
                print_row += 3
                
    def draw_weather(self, forecast):
        
        weather_top = 10
        weather_left = 55
        weather_prec_prob = 57
        
        self.screen.text('Weather forecast', weather_top, weather_left)
        weather_top += 2
        
        weather_left_px = 550
        weather_top_px = 110
        weather_temp_left_px = 620
        
        for f in forecast:
            self.screen.text(f['dt_format'], weather_top, weather_left)
            weather_top += 2
            
            if f['dt_format'] == 'Today':
                self.screen.text_sans('{}C'.format(f['temp']), weather_top_px, weather_temp_left_px)
                weather_top_px += 20
                weather_top += 2
            
            self.screen.text_sans('{}C - {}C'.format(f['tempmin'], f['tempmax']), weather_top_px, weather_temp_left_px)                
            weather_top_px += 20
            
            if f['preciptype'] is not None and f['preciptype'] != 'None' and len(f['preciptype']) > 0:
                if isinstance(f['preciptype'], str):
                    precip = f['preciptype']
                else:
                    precip = ', '.join(f['preciptype'])
                    
                self.screen.text('~{}%'.format(int(f['precipprob'])), weather_top, weather_prec_prob)
                self.screen.text_sans(precip, weather_top_px, weather_temp_left_px)
                weather_top += 2
                weather_top_px += 20
                if f['dt_format'] == 'Today':
                    self.announce_precip_today = precip
                if f['dt_format'] == 'Tomorrow':
                    self.announce_precip_tomorrow = precip
                
            weather_top += 1
            weather_top_px += 10
                
    def draw_calendar(self):
        self.screen.text_sans(str(self.year), 5, self.screen.x_middle - Calendar.LETTER_WIDTH * 2)        
        self.screen.text_courier(DateUtil.months[self.month - 1], 35, int(self.screen.x_middle - Calendar.LETTER_WIDTH * len(DateUtil.months[self.month - 1]) / 2))
        
        day = 1
        wday = self.weekday_1st
        day_row = 1
        while day <= self.days:
            day_str = str(day)
            if len(day_str) == 1: day_str = ' ' + day_str
            coordinate = self.day_coordinates[day - 1]
            self.screen.text_courier(day_str,
                                     coordinate[0], coordinate[1],
                                     red=(wday in [5,6]),
                                     inverse=(day == self.mday))
            
            day += 1
            wday += 1
            if wday > 6:
                wday = 0
                day_row += 1
                
    def draw_announcements(self):
        if not self.announce_gs_today and not self.announce_gs_tomorrow and not self.announce_precip_today and not self.announce_precip_tomorrow:
            return
        
        
        self.screen.text_sans('Announcements', 240, self.left_border_px)
        
        next_announcement_row = 260
        
        if self.announce_gs_today or self.announce_gs_tomorrow:
            line = "Garbage collection "
            if self.announce_gs_today and self.announce_gs_tomorrow:
                line += "TODAY and TOMORROW"
            elif self.announce_gs_today:
                line += "TODAY"
            elif self.announce_gs_tomorrow:
                line += "TOMORROW"

            self.screen.text_sans(line, next_announcement_row, self.left_border_px)
            next_announcement_row += 20
            
        if self.announce_precip_today:
            self.screen.text_sans('Today is {}'.format(self.announce_precip_today), next_announcement_row, self.left_border_px)
            next_announcement_row += 20

        if self.announce_precip_tomorrow:
            self.screen.text_sans('Tomorrow is {}'.format(self.announce_precip_today), next_announcement_row, self.left_border_px)
            next_announcement_row += 20

    def draw_last_updated(self):
        self.screen.text('Last updated {ddd} at {hh}:{mm}'.format(ddd=DateUtil.date_to_nice(self.today), hh=self.today[3], mm=self.today[4]), 48, 25)
        
