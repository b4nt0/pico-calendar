from epaper import Screen
from calendar import Calendar
from garbage import Garbage
from weather import Weather
from machine import RTC
import network
import secrets
import time
import urequests
import gc
import micropython
import sys

# Requires https://ghubcoder.github.io/posts/pico-w-deep-sleep-with-micropython/
import picosleep


led_yellow = machine.Pin(15, machine.Pin.OUT)
error = False
notification = False
wlan = network.WLAN(network.STA_IF)

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
    


def calendar_update():
    global wlan
    
    # ebb = bytearray(Screen.EPD_WIDTH * Screen.EPD_HEIGHT // 8)
    # erb = bytearray(Screen.EPD_WIDTH * Screen.EPD_HEIGHT // 8)
    ebb = None
    erb = None

    print('Free memory with buffers {}'.format(gc.mem_free()))

    connect()
    if not wlan.isconnected():
       # Can't connect, print a message
       print("can't connect to wifi")
       raise Exception("Can't connect to wifi")
        
    else:
        print('success')
        
        # Get current date
        print('Getting current date/time...')
        date_time_r = urequests.get("http://date.jsontest.com")
        try:
            print('Done', date_time_r)
             
            ms = date_time_r.json()['milliseconds_since_epoch']
            dt = time.localtime(int(ms / 1000))
            
        finally:
            date_time_r.close()

        # rtc = machine.RTC()
        # rtc.datetime((dt[0], dt[1], dt[2], dt[6], dt[3], dt[4], dt[5], 0))
        print('Received datetime: ', dt)
        
        del ms
        gc.collect()
         
        # Get garbage schedule
        print('Free memory {}'.format(gc.mem_free()))
        print('Getting garbage schedule...')
        garbage = Garbage()
        
        print(' - getting a token...')
        garbage.get_token()
        
        print(' - getting schedule...')
        schedule = garbage.get_schedule(dt)
        for s in schedule:
            print(s)
            
        del garbage
        gc.collect()        
        
        # Get weather
        weather = Weather()
        forecast = weather.get_weather(dt)
        
        del weather
        
        disconnect()
        
        gc.collect()
        
        # Draw calendar
        epd = Screen(ebb, erb)        
        try:
            epd.Clear()
            
            calendar = Calendar(epd, dt)
            calendar.draw_calendar()
            calendar.draw_garbage(schedule)
            calendar.draw_weather(forecast)
            calendar.draw_announcements()
            calendar.draw_last_updated()
            
            important_announcement = calendar.announce_gs_today or calendar.announce_gs_tomorrow
            
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
    led_yellow.value(1)
    result = False
    exception = False
    try:
        result = calendar_update();
    except Exception as e:
        exception = True
        sys.print_exception(e)

    led_yellow.value(0)
    gc.collect()        
    print('Free memory {}'.format(gc.mem_free()))
    return (result, exception)


def light_sleep_long(duration_seconds):
    max_light_sleep = 5 * 1
    duration = duration_seconds
    
    print('Sleeping for {} sec, in pieces of {} sec'.format(duration_seconds, max_light_sleep))
    
    while duration > 0:
        time.sleep_ms(100)
        duration -= 1
        
        if duration >= max_light_sleep:
            # machine.lightsleep(max_light_sleep * 1000)
            picosleep.seconds(max_light_sleep)
            duration -= max_light_sleep
        else:
            # machine.lightsleep(duration * 1000)
            picosleep.seconds(duration)
            duration = 0
            
        print('zzz... {}'.format(duration))


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
    #while sleep_time > 0:
    #    led_yellow.toggle()
    #    time.sleep(5)
    #    sleep_time -= 5
    print('For now just sleep anyway')
    light_sleep_long(sleep_time)
    
else:
    print('Error...')
    
    sleep_time = 60 * 60 * 1
    
    while sleep_time > 0:
        led_yellow.toggle()
        light_sleep_long(2)
        sleep_time -= 2
        
machine.reset()