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

# Requires https://ghubcoder.github.io/posts/pico-w-deep-sleep-with-micropython/
import picosleep


led_yellow = machine.Pin(15, machine.Pin.OUT)
error = False
notification = False


def calendar_update():
    # ebb = bytearray(Screen.EPD_WIDTH * Screen.EPD_HEIGHT // 8)
    # erb = bytearray(Screen.EPD_WIDTH * Screen.EPD_HEIGHT // 8)
    ebb = None
    erb = None

    print('Free memory with buffers {}'.format(gc.mem_free()))

    # Establish an internet connection
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(secrets.WIFI_SSID, secrets.WIFI_PASSWORD)
    
    attempts = 5
    print("Attempting to connect...", end='')
    while not wlan.isconnected() and attempts > 0:
        time.sleep(1)
        print('.', end='')
        attempts = attempts - 1
        
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
        import sys
        sys.print_exception(e)

    led_yellow.value(0)
    gc.collect()        
    print('Free memory {}'.format(gc.mem_free()))
    return (result, exception)


def light_sleep_long(duration_seconds):
    max_light_sleep = 60 * 70
    duration = duration_seconds
    
    while duration >= 0:
        if duration >= max_light_sleep:
            picosleep.seconds(duration)
            duration -= max_light_sleep
        else:
            picosleep.seconds(duration)
            duration = 0


(r, e) = calendar_cycle()
notification = r
error = e
sleep_time = 60 * 60 * 6
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
    while sleep_time > 0:
        led_yellow.toggle()
        light_sleep_long(2)
        sleep_time -= 2
        
machine.reset()