# Waveshare E-Paper 7.5B interface

from machine import Pin, SPI
import framebuf
import utime
from writer import Writer
import freesans20
import courier20
import gc


class ScreenImage(framebuf.FrameBuffer):
    def __init__(self, buffer, width, height):
        self.width = width
        self.height = height
        self.buffer = buffer
        self.mode = framebuf.MONO_HLSB
        super().__init__(self.buffer, self.width, self.height, self.mode)
        

class Screen:
    # Display resolution
    EPD_WIDTH       = 800
    EPD_HEIGHT      = 480

    RST_PIN         = 12
    DC_PIN          = 8
    CS_PIN          = 9
    BUSY_PIN        = 13

    EPD_TEXT_WIDTH = 80
    EPD_TEXT_HEIGHT = 48

    def __init__(self):
        self.reset_pin = Pin(Screen.RST_PIN, Pin.OUT)
        
        self.busy_pin = Pin(Screen.BUSY_PIN, Pin.IN, Pin.PULL_UP)
        self.cs_pin = Pin(Screen.CS_PIN, Pin.OUT)
        self.width = Screen.EPD_WIDTH
        self.height = Screen.EPD_HEIGHT
        self.x_middle = int(self.width / 2)
        self.text_row = 1
        
        self.spi = SPI(1)
        self.spi.init(baudrate=4000_000)
        self.dc_pin = Pin(Screen.DC_PIN, Pin.OUT)        

        print('Free memory before buffer black {}'.format(gc.mem_free()))
        self.buffer_black = bytearray(self.height * self.width // 8)
        gc.collect()
        print('Free memory before buffer red {}'.format(gc.mem_free()))
        self.buffer_red = bytearray(self.height * self.width // 8)
        gc.collect()
        
        print('Free memory before images {}'.format(gc.mem_free()))
        self.imageblack = ScreenImage(self.buffer_black, self.width, self.height)
        self.imagered = ScreenImage(self.buffer_red, self.width, self.height)
        print('Free memory after images {}'.format(gc.mem_free()))
        self.imageblack.fill(0xff)
        self.imagered.fill(0x00)
        
        self.writer_sans_black = Writer(self.imageblack, freesans20)
        self.writer_sans_red = Writer(self.imagered, freesans20)
        self.writer_courier_black = Writer(self.imageblack, courier20)
        self.writer_courier_red = Writer(self.imagered, courier20)
    
        self.init()
        
    def text(self, text_str, row=0, col=1, red=False):
        display_row = row if row > 0 else self.text_row
        
        if display_row > Screen.EPD_TEXT_HEIGHT: return
        if col + len(text_str) > Screen.EPD_TEXT_WIDTH: return
        
        image = self.imageblack if not red else self.imagered
        
        image.text(text_str, 1 + (col - 1) * 10, 1 + (display_row - 1) * 10, 0x00 if not red else 0xff)
        if row == 0: self.text_row += 1
        
    def text_sans(self, text_str, row, col, red=False):
        image = self.imageblack if not red else self.imagered
        writer = self.writer_sans_black if not red else self.writer_sans_red
        Writer.set_textpos(image, row, col)
        writer.printstring(text_str, invert=not red)        

    def text_courier(self, text_str, row, col, red=False, inverse=False):
        image = self.imageblack if not red else self.imagered
        writer = self.writer_courier_black if not red else self.writer_courier_red
        Writer.set_textpos(image, row, col)
        writer.printstring(text_str, invert=not red if not inverse else red)
        
    def digital_write(self, pin, value):
        pin.value(value)

    def digital_read(self, pin):
        return pin.value()

    def delay_ms(self, delaytime):
        utime.sleep(delaytime / 1000.0)

    def spi_writebyte(self, data):
        self.spi.write(bytearray(data))

    def module_exit(self):
        self.digital_write(self.reset_pin, 0)

    # Hardware reset
    def reset(self):
        self.digital_write(self.reset_pin, 1)
        self.delay_ms(200) 
        self.digital_write(self.reset_pin, 0)
        self.delay_ms(2)
        self.digital_write(self.reset_pin, 1)
        self.delay_ms(200)   

    def send_command(self, command):
        self.digital_write(self.dc_pin, 0)
        self.digital_write(self.cs_pin, 0)
        self.spi_writebyte([command])
        self.digital_write(self.cs_pin, 1)

    def send_data(self, data):
        self.digital_write(self.dc_pin, 1)
        self.digital_write(self.cs_pin, 0)
        self.spi_writebyte([data])
        self.digital_write(self.cs_pin, 1)

    def WaitUntilIdle(self):
        print("waiting until screen idle... ", end='')
        while(self.digital_read(self.busy_pin) == 0):   # Wait until the busy_pin goes LOW
            self.delay_ms(20)
            print('.', end='')
        self.delay_ms(20) 
        print("done")  

    def TurnOnDisplay(self):
        self.send_command(0x12) # DISPLAY REFRESH
        self.delay_ms(100)      #!!!The delay here is necessary, 200uS at least!!!
        self.WaitUntilIdle()
        
    def init(self):
        # EPD hardware init start     
        self.reset()
        
        self.send_command(0x06)     # btst
        self.send_data(0x17)
        self.send_data(0x17)
        self.send_data(0x28)        # If an exception is displayed, try using 0x38
        self.send_data(0x17)
        
#         self.send_command(0x01)  # POWER SETTING
#         self.send_data(0x07)
#         self.send_data(0x07)     # VGH=20V,VGL=-20V
#         self.send_data(0x3f)     # VDH=15V
#         self.send_data(0x3f)     # VDL=-15V
        
        self.send_command(0x04)  # POWER ON
        self.delay_ms(100)
        self.WaitUntilIdle()

        self.send_command(0X00)   # PANNEL SETTING
        self.send_data(0x0F)      # KW-3f   KWR-2F	BWROTP 0f	BWOTP 1f

        self.send_command(0x61)     # tres
        self.send_data(0x03)     # source 800
        self.send_data(0x20)
        self.send_data(0x01)     # gate 480
        self.send_data(0xE0)

        self.send_command(0X15)
        self.send_data(0x00)

        self.send_command(0X50)     # VCOM AND DATA INTERVAL SETTING
        self.send_data(0x11)
        self.send_data(0x07)

        self.send_command(0X60)     # TCON SETTING
        self.send_data(0x22)

        self.send_command(0x65)     # Resolution setting
        self.send_data(0x00)
        self.send_data(0x00)     # 800*480
        self.send_data(0x00)
        self.send_data(0x00)
        
        return 0;

    def Clear(self):
        
        high = self.height
        if( self.width % 8 == 0) :
            wide =  self.width // 8
        else :
            wide =  self.width // 8 + 1
        
        self.send_command(0x10) 
        for j in range(0, high):
            for i in range(0, wide):
                self.send_data(0xff)
                
        self.send_command(0x13) 
        for j in range(0, high):
            for i in range(0, wide):
                self.send_data(0x00)
                
        self.TurnOnDisplay()
        
    def ClearRed(self):
        
        high = self.height
        if( self.width % 8 == 0) :
            wide =  self.width // 8
        else :
            wide =  self.width // 8 + 1
        
        self.send_command(0x10) 
        for j in range(0, high):
            for i in range(0, wide):
                self.send_data(0xff)
                
        self.send_command(0x13) 
        for j in range(0, high):
            for i in range(0, wide):
                self.send_data(0xff)
                
        self.TurnOnDisplay()
        
    def ClearBlack(self):
        
        high = self.height
        if( self.width % 8 == 0) :
            wide =  self.width // 8
        else :
            wide =  self.width // 8 + 1
        
        self.send_command(0x10) 
        for j in range(0, high):
            for i in range(0, wide):
                self.send_data(0x00)
                
        self.send_command(0x13) 
        for j in range(0, high):
            for i in range(0, wide):
                self.send_data(0x00)
                
        self.TurnOnDisplay()
        
    def display(self):
        
        high = self.height
        if( self.width % 8 == 0) :
            wide =  self.width // 8
        else :
            wide =  self.width // 8 + 1
        
        # send black data
        self.send_command(0x10) 
        for j in range(0, high):
            for i in range(0, wide):
                self.send_data(self.buffer_black[i + j * wide])
            
        # send red data
        self.send_command(0x13) 
        for j in range(0, high):
            for i in range(0, wide):
                self.send_data(self.buffer_red[i + j * wide])
                
        self.TurnOnDisplay()


    def sleep(self):
        self.send_command(0x02) # power off
        self.WaitUntilIdle()
        self.send_command(0x07) # deep sleep
        self.send_data(0xa5)
