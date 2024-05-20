import time
from i2c_lcd import put_line


class DateUtil:
    months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
    days_of_week = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    short_days_of_week = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
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
    def add_hours(dt_tuple, hours=1):
        dt_seconds = time.mktime(dt_tuple)
        dt_seconds += hours * 60 * 60
        return time.localtime(dt_seconds)
    
    @staticmethod
    def dow(dt_tuple):
        return DateUtil.short_days_of_week[dt_tuple[6]]
    
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

    def __init__(self, announce_day):
        self.announce_day = announce_day
        
        self.year = self.announce_day[0]
        self.month = self.announce_day[1]
        self.mday = self.announce_day[2]
        self.weekday = self.announce_day[6]
        
        self.huisvuil = False
        self.gft = False
        self.pmd = False
        self.papier = False
        
        
    # Garbage goes on Line 0    
    def draw_garbage(self, garbage_schedule):
        if len(garbage_schedule) == 0:
            put_line('No garbage')
            
        else:
            announcement = DateUtil.dow(self.announce_day) + ': '
            for item in garbage_schedule:
                if not DateUtil.dates_equal(item['date'], self.announce_day):
                    continue
                
                gtype = item['type'].lower()
                if gtype.startswith('gft'):
                    announcement += 'GFT '
                    self.gft = True
                elif gtype.startswith('huisvuil'):
                    announcement += 'Huis '
                    self.huisvuil = True
                elif 'pmd' in gtype:
                    announcement += 'PMD '
                    self.pmd = True
                elif 'papier' in gtype or 'karton' in gtype:
                    announcement += 'Papier '
                    self.papier = True
                else:
                    announcement += gtype[0:3]
                    
            put_line(announcement.strip(), 0)
                
    def draw_weather(self, forecast):
        announcement = ''
        for f in forecast:
            if not DateUtil.dates_equal(f['date'], self.announce_day):
                continue
            
            announcement = '{}~{}C '.format(int(f['tempmin']), int(f['tempmax'])) # Can be up to 9 chars: -25~-23C
            
            if f['preciptype'] is not None and f['preciptype'] != 'None' and len(f['preciptype']) > 0:
                if isinstance(f['preciptype'], str):
                    precip = f['preciptype']
                else:
                    precip = ', '.join(f['preciptype'])
                    
                announcement += precip
                
        put_line(announcement.strip(), 1)
