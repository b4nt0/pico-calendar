# from ecowerf import Ecowerf
from epaper import Screen


class Calendar:
    def __init__(self, screen):
        self.screen = screen

    def draw_calendar(self, year, month, mday, weekday):
        # Year is 4 digits, e.g. 2022
        # Month is 1-12
        # Mday is 1-31
        # Weekday is 0-6 for Mon-Sun
        
        self.screen.text_sans(str(year), 5, self.screen.x_middle - 40)
        
        months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
        days_in_months = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        self.screen.text_courier(months[month - 1], 35, self.screen.x_middle - 20 * len(months[month - 1]))
        
        week_excess_from_1st = (mday - 1) % 7
        weekday_1st = (weekday - week_excess_from_1st + 7) % 7
        
        day_col_width_px = 60
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
                                     first_day_row_start_px + 20 * day_row, first_day_col_start_px + (wday - 1) * day_col_width_px,
                                     red=(wday in [5,6]),
                                     inverse=(day == mday))
            
            day += 1
            wday += 1
            if wday > 6:
                wday = 0
                day_row += 1
    


if __name__=='__main__':
    
    #ecowerf = Ecowerf()
    #t = ecowerf.get_token()
    #print(t)
    
    epd = Screen()
    epd.Clear()
    
    calendar = Calendar(epd)
    calendar.draw_calendar(2022, 8, 5, 4)
    
    
    epd.display()
    epd.delay_ms(500)
    
    if False:
        epd.Clear()
        epd.delay_ms(2000)
        print("sleep")
        epd.sleep()
