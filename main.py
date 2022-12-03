from epaper import Screen
from machine import RTC
import network
import secrets
import time
import gc
import micropython

debugging = False

led_yellow = machine.Pin(15, machine.Pin.OUT)
button = machine.Pin(16, machine.Pin.IN, machine.Pin.PULL_DOWN)
rtc = machine.RTC()

error = False
notification = False
wlan = network.WLAN(network.STA_IF)

def print_mem_info(label=None):
    global debugging
    
    if debugging:
        if label is not None:
            print(label)
        print('Free memory with buffers {}'.format(gc.mem_free()))
        micropython.mem_info(True)        

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


def light_if_allowed():
    global led_yellow
    global rtc
    
    dt = rtc.datetime()
    month = dt[1]
    hour = dt[4]
    
    del dt
    
    if month >= 11 or month <= 3:
        hour += 1  # Winter time
    else:
        hour += 2  # Summer time
        
    if hour < 7 or hour > 22:
        return
   
    led_yellow.value(1)           


def was_there_alarm_today():
    global rtc
    
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
        last_day = day
        
    print('Last blinked on {}, today is {}'.format(last_day, day))
            
    return last_day != day


def snooze():
    dt = rtc.datetime()
    day = dt[2]

    print('Snoozed on {}'.format(day))
    
    tfile = open("last_blink.txt", "w")
    try:
        tfile.write(day)
    finally:
        tfile.close()
        del tfile


def calendar_update():
    global wlan
    global rtc
    
    #ebb = bytearray(Screen.EPD_WIDTH * Screen.EPD_HEIGHT // 8)
    #erb = bytearray(Screen.EPD_WIDTH * Screen.EPD_HEIGHT // 8)
    ebb = None
    erb = None

    print_mem_info()

    connect()
    
    if not wlan.isconnected():
       # Can't connect, print a message
       print("can't connect to wifi")
       raise Exception("Can't connect to wifi")
        
    else:
        print('success')
        
        # Get current date
        print('Getting current date/time...')
        
        import urequests
        date_time_r = urequests.get("http://date.jsontest.com")
        try:
            print('Done', date_time_r)
             
            ms = date_time_r.json()['milliseconds_since_epoch']
            dt = time.localtime(int(ms / 1000))
            
        finally:
            date_time_r.close()

        rtc.datetime((dt[0], dt[1], dt[2], dt[6], dt[3], dt[4], dt[5], 0))
        print('Received datetime: ', dt)
        
        del ms
        del urequests
        
        light_if_allowed()

        gc.collect()
        
        print_mem_info('1')

        from garbage import Garbage
        # Get garbage schedule
        print('Free memory {}'.format(gc.mem_free()))
        print('Getting garbage schedule...')
        garbage = Garbage()
        
        print(' - getting a token...')
        garbage.get_token()
        
        gc.collect()
        
        print_mem_info('2')
       
        print(' - getting schedule...')
        schedule = garbage.get_schedule(dt)
        for s in schedule:
            print(s)
            
        del garbage
        del Garbage
        
        gc.collect()
        
        print_mem_info('3')
        
        from weather import Weather
        
        # Get weather
        weather = Weather()
        forecast = weather.get_weather(dt)
        
        del weather
        del Weather
        
        disconnect()
        
        gc.collect()
        
        print_mem_info('4')
        
        # Draw calendar
        from calendar import Calendar
        epd = Screen(ebb, erb)        
        try:
            epd.Clear()
            
            calendar = Calendar(epd, dt)
            calendar.draw_calendar()
            calendar.draw_garbage(schedule)
            calendar.draw_weather(forecast)
            calendar.draw_announcements()
            calendar.draw_last_updated()
            
            important_announcement = calendar.announce_gs_tomorrow
            
            epd.display()
            epd.delay_ms(500)
                
            epd.delay_ms(2000)
        
        finally:
            print("Screen sleep")
            epd.sleep()
        
        print('All done')
    return important_announcement
        

def calendar_cycle():
    gc.collect()
    print('Free memory {}'.format(gc.mem_free()))

    result = False
    exception = False
    try:
        result = calendar_update();
    except Exception as e:
        import sys
        
        exception = True
        sys.print_exception(e)
        
        micropython.mem_info(True)
        
        # Log last exception
        efile = open("last_exception.txt", "w")
        sys.print_exception(e, efile)
        efile.close()

    led_yellow.value(0)
    gc.collect()        
    print('Free memory {}'.format(gc.mem_free()))
    return (result, exception)


def light_sleep_long(duration_seconds, ignore_button=False):
    global button
    
    if duration_seconds <= 0: return True
    
    max_light_sleep = 5 * 1
    duration = duration_seconds
    
    accumulated01 = 0
    while duration > 0:
        if not ignore_button and button.value() == 1:
            return False
        
        time.sleep_ms(100)
        accumulated01 += 1
        if accumulated01 == 10:
          duration -= 1
          accumulated01 = 0
        
        if duration == 0: return True
        
        if duration >= max_light_sleep:
            # machine.lightsleep(max_light_sleep * 1000)
            # picosleep.seconds(max_light_sleep)

            # Dormant sleep does not wake up :(
            time.sleep(max_light_sleep)
            duration -= max_light_sleep
        else:
            # machine.lightsleep(duration * 1000)
            # picosleep.seconds(duration)
            
            # Dormant sleep does not wake up :(
            time.sleep(max_light_sleep)
            duration = 0
            
    return True
            

micropython.alloc_emergency_exception_buf(100)
(r, e) = calendar_cycle()
notification = r
error = e
sleep_time = 60 * 60 * 4

disconnect()

if not error and not notification:
    print('Sleeping...')
    # time.sleep(sleep_time)
    light_sleep_long(sleep_time)
    
elif not error and notification:
    print('Notification...')
    
    already_alarmed = was_there_alarm_today()    
    while sleep_time > 0:
        led_yellow.value(0)
        result = light_sleep_long(5)
        if not result:
            snooze()
            break
        
        if not already_alarmed: light_if_allowed()        
        result = light_sleep_long(1)
        if not result:
            snooze()
            break
        sleep_time -= 7
        
    led_yellow.value(0)
    
    if sleep_time > 0:
        light_sleep_long(10, True)
        sleep_time -= 10
        light_sleep_long(sleep_time)
   
else:
    print('Error...')
    
    sleep_time = 60 * 60 * 1
    
    while sleep_time > 0:
        light_if_allowed()
        result = light_sleep_long(2)
        led_yellow.value(0)
        if not result: break
        result = light_sleep_long(2)
        if not result: break
        sleep_time -= 2
        
machine.reset()