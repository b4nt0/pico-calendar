# Calendar & reminder
# -------------------

# Hard-coded configuration
# ------------------------
# DST correction
# Do-not-disturb hours
# Before 1pm = today's events, otherwise tomorrow's events

# Garbage reminder for tomorrow or today
# --------------------------------------
# Blue LED = PMD
# Yellow LED = Paper cardboard
# Green LED = GFT + Mixed

# Weather forecast
# ----------------
# Mini-display = Temperature range, date

# Busy/error indicator
# --------------------
# Mini-display indicates progress = In progress
# Mini-display shows error = Error occurred

# Button
# ------
# Shut down all LEDs until the next morning

from machine import RTC
import network
import secrets
import time
import gc
import micropython
from lcd import LcdApi
from i2c_lcd import I2cLcd, put_line, status, content, lcd
from calendar import DateUtil, Calendar

debugging = False

# Settings
NEXT_DAY_FORECAST_HOUR = 12
TIMEZONE_UTC_INCREMENT = 1
TOO_EARLY = 6
TOO_LATE = 11
UPDATE_EVERY_X_HOURS = 6
CHECK_LIGHTS_EVERY_X_SECONDS = 120

# LED pin numbers
LED_PMD = machine.Pin(17, machine.Pin.OUT)
LED_PAPIER = machine.Pin(15, machine.Pin.OUT)
LED_GFT = machine.Pin(14, machine.Pin.OUT)
LED_HUISVUIL = None

# Snooze pin number
snooze_button = machine.Pin(12, machine.Pin.IN, machine.Pin.PULL_DOWN)

# Real-time clock
rtc = None

# Globals
error = False
notification = False
wlan = network.WLAN(network.STA_IF)
pmd = False
papier = False
gft = False
huisvuil = False
backlight = True
snoozed = False
unsnoozed = False


def connect():
    global wlan
    
    # Establish an internet connection
    wlan.active(True)
    wlan.connect(secrets.WIFI_SSID, secrets.WIFI_PASSWORD)
    
    attempts = 5
    print("Attempting to connect...", end='')
    while not wlan.isconnected() and attempts > 0:
        time.sleep(1)
        print('.', end='')
        attempts = attempts - 1


def status_clock(line_num = 1):
    if rtc is None: return
    dt = rtc.datetime()
    day = dt[2]
    month = dt[1]
    year = dt[0] % 100
    hour = dt[4]
    minute = dt[5]
    timestring="%02d-%02d-%02d %02d:%02d"%(day, month, year, hour, minute)
    put_line(timestring, line_num)
    

def disconnect():
    # Disconnect LAN
    global wlan
    
    if not wlan.isconnected(): return
    
    wlan.disconnect()
    wlan.active(False)
    attempts = 5
    print("Attempting to disconnect...", end='')
    while wlan.isconnected() and attempts > 0:
        time.sleep(1)
        print('.', end='')
        attempts = attempts - 1
        
        
def correct_for_timezone(local_time):
    month = local_time[1]

    if month >= 11 or month <= 3:
        hour = TIMEZONE_UTC_INCREMENT      # Winter time
    else:
        hour = TIMEZONE_UTC_INCREMENT + 1  # Summer time
        
    return DateUtil.add_hours(local_time, hour)


def light(led):
    if led is None:
        return
    
    led.value(1)
    

def dim(led):
    if led is None:
        return
    
    led.value(0)
    

def dim_all():
    global backlight
    
    if backlight:
      lcd.hal_backlight_off()
      backlight = False
      
    dim(LED_GFT)
    dim(LED_PMD)
    dim(LED_PAPIER)
    dim(LED_HUISVUIL)
    

def was_there_alarm_today():
    if rtc is None:
        return False
    
    dt = rtc.datetime()
    day = dt[2]    
    del dt

    try:
        tfile = open("last_blink.txt", "r")
        try:
            last_day = int(tfile.read())
        finally:
            tfile.close()
            del tfile
    except:
        last_day = day - 1
        
    print('Last blinked on {}, today is {}'.format(last_day, day))
            
    return last_day == day


def check_lights():
    global backlight
    
    if rtc is None: return
    
    dt = rtc.datetime()
    hour = dt[4]        
    del dt
    
    print('Hour {} WTAT {} Unsnoozed {}'.format(hour, was_there_alarm_today(), unsnoozed))
    
    if (hour < TOO_EARLY or hour > TOO_LATE or was_there_alarm_today()) and not unsnoozed:
        dim_all()
        return
    
    # Light up the screen
    if not backlight:
        lcd.hal_backlight_on()
        backlight = True
    
    # Light the lights
    if gft: light(LED_GFT)
    else: dim(LED_GFT)
    
    if pmd: light(LED_PMD)
    else: dim(LED_PMD)
    
    if huisvuil: light(LED_HUISVUIL)
    else: dim(LED_HUISVUIL)
    
    if papier: light(LED_PAPIER)
    else: dim(LED_PAPIER)


def snooze():
    global snoozed
    global unsnoozed

    if unsnoozed and backlight and not snoozed:
        # Snooze back
        unsnoozed = False
        
    if snoozed:
        # Second press on the 'Snooze' button causes reset
        machine.reset()
        
    # Check if we're now on or off
    if backlight:
        snoozed = True
        dim_all()
        
        if rtc is None:
            return
        
        dt = rtc.datetime()
        day = dt[2]

        print('Snoozed on {}'.format(day))
    
        tfile = open("last_blink.txt", "w")
        try:
            tfile.write(str(day))
        finally:
            tfile.close()
            del tfile
            
    else:
        print('Unsnoozed')
        unsnoozed = True
        check_lights()


def calendar_update():
    global wlan
    global rtc
    
    status('Connecting...')
    connect()
    
    if not wlan.isconnected():
       # Can't connect, print a message
       print("can't connect to wifi")
       content('No Wi-Fi')
       raise Exception("Can't connect to wifi")
        
    else:
        print('success')
        
        # Get current date
        print('Getting current date/time...')
        status('Get time...')
        
        import urequests
        date_time_r = urequests.get("http://date.jsontest.com")
        try:
            print('Done', date_time_r)
             
            ms = date_time_r.json()['milliseconds_since_epoch']
            dt = time.localtime(int(ms / 1000))
            dt = correct_for_timezone(dt)
            
        finally:
            date_time_r.close()

        rtc = machine.RTC()
        rtc.datetime((dt[0], dt[1], dt[2], dt[6], dt[3], dt[4], dt[5], 0))
        status_clock(0)
        print('Received datetime: ', dt)
        
        del ms
        del urequests
        
        # Define what date to announce for
        announce_dt = dt if dt[3] < NEXT_DAY_FORECAST_HOUR else DateUtil.add_days(dt, 1)
        
        # Get garbage schedule
        print('Getting garbage schedule...')
        status('Update garbage..')

        from garbage import Garbage
        garbage = Garbage()
        
        print(' - getting a token...')
        garbage.get_token()
        
        print(' - getting schedule...')
        schedule = garbage.get_schedule(announce_dt)
        for s in schedule:
            print(s)
            
        del garbage
        del Garbage
        
        # Get weather
        print('Getting weather schedule...')
        status('Update weather..')
        from weather import Weather
        
        weather = Weather()
        forecast = weather.get_weather(announce_dt)
        print(forecast)
        
        del weather
        del Weather
        
        disconnect()
        
        # Draw calendar status
        calendar = Calendar(announce_dt)
        calendar.draw_weather(forecast)
        calendar.draw_garbage(schedule)
        
        global pmd
        global gft
        global huisvuil
        global papier
        
        pmd = calendar.pmd
        gft = calendar.gft
        huisvuil = calendar.huisvuil
        papier = calendar.papier
        print('PMD {}, GFT {}, HV {}, PK {}'.format(pmd, gft, huisvuil, papier))
        
        print('All done')
        
        
try:
    time.sleep(1)
    lcd.clear()
    status('Updating...')
    calendar_update()
    
    sleep_time = 60 * 60 * UPDATE_EVERY_X_HOURS
    
    # Sleep, but check the button and the lights every now and then
    light_check_counter = 1
    while sleep_time > 0:
        time.sleep(1)
        if snooze_button.value() == 1:
            snooze()
                
        sleep_time -= 1
        light_check_counter -= 1
        
        if light_check_counter <= 0:
            check_lights()
            light_check_counter = CHECK_LIGHTS_EVERY_X_SECONDS
        
    machine.reset()
        
except Exception as e:
    import sys
    
    exception = True
    sys.print_exception(e)
    
    # Log last exception
    efile = open("last_exception.txt", "w")
    try:
        sys.print_exception(e, efile)
    finally:
        efile.close()
        
    status("Can't update")
