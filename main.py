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
import ntptime
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
    
    attempts = 10
    print("Attempting to connect...", end='')
    while not wlan.isconnected() and attempts > 0:
        status(f'Connecting {attempts}')
        time.sleep(11 - attempts)
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
        
        
def correct_for_timezone():
    local_time = time.localtime() 
    month = local_time[1]

    if month >= 11 or month <= 3:
        hour = TIMEZONE_UTC_INCREMENT      # Winter time
    else:
        hour = TIMEZONE_UTC_INCREMENT + 1  # Summer time
        
    corrected_time = DateUtil.add_hours(local_time, hour)
    rtc_time = (
        corrected_time[0],
        corrected_time[1],
        corrected_time[2],
        corrected_time[6],
        corrected_time[3],
        corrected_time[4],
        corrected_time[5],
        0
    )

    rtc.datetime(rtc_time)

def light(led):
    if led is None:
        return
    
    led.value(1)
    

def dim(led):
    if led is None:
        return
    
    led.value(0)
    

def dim_all(force = False):
    global backlight
    
    if backlight or force:
        lcd.hal_backlight_off()
        backlight = False
      
    dim(LED_GFT)
    dim(LED_PMD)
    dim(LED_PAPIER)
    dim(LED_HUISVUIL)
    

def was_there_alarm_today():
    if snoozed and not unsnoozed:
        return True
    
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
    
    print('Hour {}, was there alarm today {}, unsnoozed {}'.format(hour, was_there_alarm_today(), unsnoozed))
    
    if (hour < TOO_EARLY or hour > TOO_LATE or was_there_alarm_today()) and not unsnoozed and not debugging:
        print('No-disturb hours, dimming')
        dim_all()
        return
    
    # Light up the screen
    if not backlight:
        print('Lighting!')
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
    
    dim_all()
    
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
        
        attempts = 5
        while attempts > 0:
            try:
                ntptime.settime()
                break
            except:
                attempts -= 1
                time.sleep(1)
                
        dt = time.localtime()
        rtc = machine.RTC()
        
        correct_for_timezone()
        status_clock(0)
        print('Received datetime: ', dt)
        
        check_lights()
        
        # Define what date to announce for
        announce_dt = dt if dt[3] < NEXT_DAY_FORECAST_HOUR else DateUtil.add_days(dt, 1)
        
        # Get garbage schedule
        print('Getting garbage schedule...')
        status('Update garbage..')

        from garbage import Garbage
        garbage = Garbage()
        
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
        
        pmd = calendar.pmd or debugging
        gft = calendar.gft or debugging
        huisvuil = calendar.huisvuil or debugging
        papier = calendar.papier or debugging
        print('PMD {}, GFT {}, HV {}, PK {}'.format(pmd, gft, huisvuil, papier))
        
        print('All done')
        
        
sleep_time = 60 * 60 * UPDATE_EVERY_X_HOURS

try:
    time.sleep(1)
    lcd.clear()
    status('Updating...')
    calendar_update()
    
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

finally:
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
        
