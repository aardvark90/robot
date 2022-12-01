#pi pico robot V11.3
#1-Dec-2022
#Dave Gunning, Aardvark Designs


from machine import Pin, I2C, PWM
import framebuf,sys,utime
from utime import sleep

# Import MicoPython max7219 library for 8x8 matrix display
from machine import SPI
import max7219

import time

#Import MicoPython ILI9341 library for 2.4" TFT LCD waveshare
#Note that image files need to use color565 raw binary format
from ili9341 import Display, color565

from sys import implementation

###### GPIO #######

# leds
led = machine.Pin(25,machine.Pin.OUT)
led.value(1)
led20 = machine.Pin(20,machine.Pin.OUT)
led20.value(0)
led21 = machine.Pin(21,machine.Pin.OUT)
led21.value(0)
led22 = machine.Pin(22,machine.Pin.OUT)
led22.value(0)

#magnet
magnet = machine.Pin(17,machine.Pin.OUT)

#### servos
#MG995 servo, PWM pulse widths in micro seconds
MID = 4000
MIN = 1000
MAX = 4000
#maxDuty PWM cycle is 2ms at a frequency of @20ms/50Hz ie 10% of 65353
minDuty = 2000
maxDuty = 9000
#right arm
rightArm = PWM(Pin(14))
rightArm.freq(50)
#left arm
leftArm = PWM(Pin(13))
leftArm.freq(50)
#head
head = PWM(Pin(15))
head.freq(50)
#amber head LED
headLED = PWM(Pin(12))
head.freq(50)

#ultrasonic detector HC-SR04
trigger = Pin(3, Pin.OUT)
#echo = Pin(2, Pin.IN)
echo = Pin(2, Pin.IN,Pin.PULL_DOWN)
failCount = 0
totalCount = 0

#MAX7219 matrix display
matrixSpi = SPI(1, baudrate=400000, polarity=1, phase=0, sck=Pin(10), mosi=Pin(27))
cs1 = Pin(9, Pin.OUT)
MSGBOARDWIDTH = 4
SCROLLSPEED = 0.03

#MAX7219 matrix face
faceSpi = SPI(0, baudrate=400000, polarity=1, phase=0, sck=Pin(6), mosi=Pin(7))
cs2 = Pin(5, Pin.OUT)
FACEWIDTH = 1
print(faceSpi)

#TFT LCD display
lcdSpi = SPI(0, baudrate=400000, sck=Pin(18), mosi=Pin(19))
cs_pin = Pin(21)
dc_pin = Pin(16)
rst_pin = Pin(20)
bl = Pin(22, Pin.OUT)
# Baud rate of 40000000 seems about the max, use 400000

#Piezo buzzer
buzzer = PWM(Pin(1))
HIBUZ = 1000
MEDBUZ = 500

# 8x8 face expressions
faceSmile=[0,0,0,0,0,0,0,0,
          0,0,0,0,0,0,0,0,
          0,0,0,0,0,0,0,0,
          1,0,0,0,0,0,0,1,
          1,0,0,0,0,0,0,1,
          0,1,0,0,0,0,1,0,
          0,0,1,1,1,1,0,0,
          0,0,0,0,0,0,0,0]

faceSad=[0,0,0,0,0,0,0,0,
          0,0,1,1,1,1,0,0,
          0,1,0,0,0,0,1,0,
          1,0,0,0,0,0,0,1,
          1,0,0,0,0,0,0,1,
          0,0,0,0,0,0,0,0,
          0,0,0,0,0,0,0,0,
          0,0,0,0,0,0,0,0]

faceSmirk=[0,0,0,0,0,0,0,0,
          0,0,0,0,0,0,0,0,
          0,0,0,0,0,0,0,0,
          1,0,0,0,0,0,0,1,
          0,1,1,1,1,1,1,0,
          0,0,0,0,0,0,0,0,
          0,0,0,0,0,0,0,0,
          0,0,0,0,0,0,0,0]

faceBlank=[0,0,0,0,0,0,0,0,
          0,0,0,0,0,0,0,0,
          0,0,0,0,0,0,0,0,
          0,0,0,0,0,0,0,0,
          0,0,0,0,0,0,0,0,
          0,0,0,0,0,0,0,0,
          0,0,0,0,0,0,0,0,
          0,0,0,0,0,0,0,0]


def ultraDetect(failCount):
    detect = False
    wait = 0
    timepassed = 0
    signalon = 0
    signaloff = 0
    
    #send a pulse
    trigger.low()
    utime.sleep_us(5)
    #utime.sleep_us(2)
    trigger.high()
    utime.sleep_us(10)
    trigger.low()
    
    #time how long the echo 0>1>0 pulse lasts
    while echo.value() == 0: 
        signaloff = utime.ticks_us()
        wait = wait +1
        #stop if we wait too long for echo to change from 0 to 1
        if wait > 3000:       
            break
    while echo.value() == 1:
        signalon = utime.ticks_us()
    
    #work out distance
    timepassed = utime.ticks_diff(signalon, signaloff)
    print(timepassed,"ms ",signalon,signaloff, "Wait", wait)
    distance = (timepassed * 0.0343) / 2
    
    #error handling
    distance = abs(distance) # remove negative distance, indicates error
    if distance > 1000: # large numbers indicate out of range
        #print("distace>1000, ultrasonic error")
        distance = 9999
    
    #display distance
    print(distance, "cm") 
    text1 = "Distance= " + str(int(distance)) +" cm"
    text2 = str(int(distance))
    #text3 = "distance"
    text3 = "range cm"
    #lcdDisplay.draw_text8x8(25,240,text1,color565(255,255,255),color565(0,0,0),0)
    displayMatrix(text3, text2, True, 1, SCROLLSPEED)
    sleep(0.5)

    if distance < 50:
        print("object detected",end=" ")
        detect = True
        
    if distance == 9999:
        print("detector error ",distance)
        failCount = failCount+1   
        detect = True 
        
    return detect,failCount

def moveRightArm(start, stop, step):
    for degrees in range (start,stop,step):       
            newDuty=minDuty+((maxDuty-minDuty)*(degrees/180))
            rightArm.duty_u16(int(newDuty))
            print("right arm",degrees,int(newDuty))
            utime.sleep(0.1)        
            
def moveLeftArm(start, stop, step):
    for degrees in range (start,stop,step):       
            newDuty=minDuty+((maxDuty-minDuty)*(degrees/180))
            leftArm.duty_u16(int(newDuty))
            print("left arm",degrees,int(newDuty))
            utime.sleep(0.1)
            
def moveHead(start, stop, step):
    for degrees in range (start,stop,step):       
            newDuty=minDuty+((maxDuty-minDuty)*(degrees/180))
            head.duty_u16(int(newDuty))
            print("head",degrees,int(newDuty))
            utime.sleep(0.1)
            
def amberModeToggle():
    #LED modes: fast rotate, slow rotate, slow strobe, fast strobe, off
    #LED modes are not selectable, power-on state is fast rotate
    #send servo angleList to LED to toggle to next mode
     
    angleList = [40,120]
    def sendPWM(angle):
        #for flashes in range (duration):       
        Duty=minDuty+((maxDuty-minDuty)*(angle/180))
        headLED.duty_u16(int(Duty))
        print("amberLED",angle,int(Duty))
        utime.sleep(0.02)
                         
    for item in angleList:
        sendPWM(item)
    
            
def setupMatrixDisplay(matrixSpi, numberOf8x8):
    #Intialize the SPI
    #matrixSpi = SPI(0, baudrate=10000000, polarity=1, phase=0, sck=Pin(6), mosi=Pin(7))
    #cs = Pin(9, Pin.OUT)

    # Create matrix display instant, which has four MAX7219 devices.
    matrixDisplay = max7219.Matrix8x8(matrixSpi, cs1, numberOf8x8)
    print("matrixDisplay")
    #Set the display brightness. Value is 1 to 15.
    matrixDisplay.brightness(3)
    return(matrixDisplay)

def setupFaceDisplay(faceSpi, numberOf8x8):
    #Intialize the SPI
    #matrixSpi = SPI(0, baudrate=10000000, polarity=1, phase=0, sck=Pin(6), mosi=Pin(7))
    #cs = Pin(9, Pin.OUT)

    # Create matrix display instant, which has four MAX7219 devices.
    faceDisplay = max7219.Matrix8x8(faceSpi, cs2, numberOf8x8)
    print("faceDisplay")
    #Set the display brightness. Value is 1 to 15.
    faceDisplay.brightness(3)
    return(faceDisplay)

def faceDisplayPixel(x,y,c):
    #set or reset pixel c at x,y within frame buffer
    #MAX7219 matrix display is x(0-7) bits high and y bits wide, where y is N*8.
    #Eg y = 0-31 in the case of 4x8x8 matrix
    faceDisplay.pixel(x,y,c)
    faceDisplay.show()


def displayMatrix(message1, message2, scroll = False, scrollCount = 10, speed = 0.05):
    #Load message1 into a frame buffer and scroll scrollCount times
    #Then, display message2, no scroll
    
    #Get the message length
    length = len(message1)

    #Calculate number of columns of the message
    column = (length * 8)

    #Clear the display.
    matrixDisplay.fill(0)
    matrixDisplay.show()

    #sleep for one one seconds
    time.sleep(1)

    while scrollCount > 0:
        for x in range(32, -column, -1):     
            #Clear the display
            matrixDisplay.fill(0)
            #print("x ",x)
            # Write the scrolling text in to frame buffer
            matrixDisplay.text(message1 ,x,0,1)
        
            #Show the display
            matrixDisplay.show()
       
            #Set the Scrolling speed. 0.05 is 50mS.
            time.sleep(speed)

        scrollCount = scrollCount -1
        
    #Clear the display
    matrixDisplay.fill(0)

    # Write the scrolling text in to frame buffer
    matrixDisplay.text(message2 ,1,0,1)
        
    #Show the display
    matrixDisplay.show()

def setupLcdDisplay():
    # Create the ILI9341 display:
    lcdDisplay = Display(lcdSpi, dc=dc_pin, cs=cs_pin, rst=rst_pin)
    #back light on
    bl.high()
    lcdDisplay.clear()
   
    return(lcdDisplay)

def displayFace(facelist):
    #input is list of 8x8 matrix pixels to be sent to MAX7219 display
    #column is block of 8x8 matrix leds
    faceDisplay.fill(0)
    faceDisplay.show()
    
    x=0
    y=0
    c=1
    for item in facelist: 
        faceDisplayPixel(x,y,item)
        #print("face",x,y,item)
        x = x+1
        if x > 7:
            x=0
            y=y+1
     
def hiBuzz(length,vol):
    print("hibuzz")
    buzzer.freq(1000)
    buzzer.duty_u16(vol)
    sleep(length)
    buzzer.duty_u16(0)
    
def medBuzz(length,vol):
    print("medbuzz")
    buzzer.freq(500)
    buzzer.duty_u16(vol)
    sleep(length)
    buzzer.duty_u16(0)
    
#--------------------------------- MAIN --------------------------------------
hiBuzz(0.5,1000)
sleep(0.1)
medBuzz(0.5,1000)

#setup LED matrix display
matrixDisplay = setupMatrixDisplay(matrixSpi,MSGBOARDWIDTH)
scrolling_message = ""
message = "Hi  "
displayMatrix(scrolling_message, message, True, 1, SCROLLSPEED)

faceDisplay = setupFaceDisplay(faceSpi,FACEWIDTH)
displayFace(faceSmile)


#setup LCD display
lcdDisplay = setupLcdDisplay()

#display
lcdDisplay.draw_image('images/image.raw', 0, 0, 240,240)


#-------------------- main loop ------------------------
while(1):
    
    hiBuzz(0.1,1000)
    medBuzz(1.0,1000)
    hiBuzz(0.1,1000)
    
    scrolling_message = "Welcome."
    message = "Hi"
    displayMatrix(scrolling_message, message, True, 1, SCROLLSPEED)
    
    #lcdDisplay.clear()
    lcdDisplay.draw_image('images/image2.raw', 0, 0, 240,320)
      
    medBuzz(0.1,1000)
    
    displayFace(faceSad)
    utime.sleep(1)
    displayFace(faceSmirk)
    utime.sleep(1)
    displayFace(faceSmile)
    utime.sleep(1)
    displayFace(faceSmirk)
    
    text1 = "Anyone nearby?"
    text2 = "Look"
    print(text1)
    #lcdDisplay.draw_text8x8(50,280,text1,color565(0,255,0),color565(0,0,0),0)
    displayMatrix(text1, text2, True, 1, SCROLLSPEED)
 
    # allow a bit of time for hand to be detected
    # for ultrsonic continuous test mode, comment out count
    count = 10
    failC = 0
    sleep(1)
    while(count>0):
        detect,failCount = ultraDetect(failCount)
        count = count-1
        totalCount = totalCount+1
        print("failCount",failCount, "out of ",totalCount)
        if detect == True:
            medBuzz(0.2,500)
            hiBuzz(0.2,1000)
            count = 0
            print("detect", end="")
        
    if detect == True:
        displayFace(faceSmile)
        utime.sleep(1)
        displayFace(faceSmirk)
        text = "Starting work"
        matrixDisplay.fill(0)
        #lcdDisplay.draw_text8x8(50,280,text,color565(255,0,0),color565(0,0,0),0)
        detect=False
    
        displayFace(faceSad)
        text1 = "Hi, let's look"
        text2 = "Look"
        #lcdDisplay.draw_text8x8(50,280,text1,color565(255,255,0),color565(0,0,0),0)
        displayMatrix(text1, text2, True, 1, SCROLLSPEED)
  
        start =90
        stop = 130
        step = 5
        moveHead(start, stop, step)
        utime.sleep(1)
        
        start =130
        stop = 90
        step = -5
        moveHead(start, stop, step)
        utime.sleep(1)
        
        start =90
        stop = 50
        step = -5
        moveHead(start, stop, step)
        utime.sleep(1)
        
        start = 50
        stop = 90
        step = 5
        moveHead(start, stop, step)
        utime.sleep(1)
        
        #find metal
        amberModeToggle()
        text1 = "Let's get something"
        text2 = "Get"
        #lcdDisplay.draw_text8x8(50,280,text1,color565(0,255,0),color565(0,0,0),0)      
        displayMatrix(text1, text2, True, 1, SCROLLSPEED)
        start = 50
        stop = 20
        step = -5
        moveRightArm(start, stop, step)
        #utime.sleep(1)
        
        text1 = "Magnet ON"
        text2 = "ON"       
        #lcdDisplay.draw_text8x8(50,280,text,color565(0,255,0),color565(0,0,0),0)
        displayMatrix(text1, text2, True, 1, SCROLLSPEED)
        hiBuzz(0.5,1000)
        magnet.value(1)
        time.sleep(1)
        
        text1 = "Lifting..."
        text2 = "Lift"
        #lcdDisplay.draw_text8x8(50,280,text,color565(0,255,0),color565(0,0,0),0)
        start = 20
        stop = 50
        step = 5
        moveRightArm(start, stop, step)
        #utime.sleep(1)
        
        text1 = "Magnet OFF"
        text2 = "Drop"
        displayFace(faceSmile)
        #lcdDisplay.draw_text8x8(50,280,text1,color565(0,255,0),color565(0,0,0),0)
        displayMatrix(text1, text2, True, 1, SCROLLSPEED)
        medBuzz(0.5,1000)
        magnet.value(0)
        #time.sleep(1)
        
        
        #wave cable
        amberModeToggle()
        displayFace(faceSmile)
        text1 = "Look at this!"
        text2 = "Look"
        #lcdDisplay.draw_text8x8(50,280,text1,color565(0,255,0),color565(0,0,0),0)
        displayMatrix(text1, text2, True, 1, SCROLLSPEED)
        start = 80
        stop = 40
        step = -5
        moveLeftArm(start, stop, step)
        utime.sleep(1)
        
        #lcdDisplay.draw_text8x8(50,280,text,color565(0,255,0),color565(0,0,0),0)
        start = 40
        stop =  80
        step = 5
        moveLeftArm(start, stop, step)
        utime.sleep(1)
  
        #lcdDisplay.draw_text8x8(50,280,text,color565(0,255,0),color565(0,0,0),0)
        start = 80
        stop =  30
        step =  -5
        moveLeftArm(start, stop, step)
        utime.sleep(1)
        
        start = 30
        stop = 80
        step = 5
        moveLeftArm(start, stop, step)
            
            
        displayFace(faceSmirk)
        utime.sleep(1)
        displayFace(faceSmile)
        utime.sleep(1)
        displayFace(faceSmirk)
        utime.sleep(1)
        displayFace(faceSmile)
            
        text1 = "Come and speak to me"
        text2 = "?"
        #lcdDisplay.draw_text8x8(50,280,text1,color565(0,255,0),color565(0,0,0),0)
        displayMatrix(text1, text2, True, 1, SCROLLSPEED)
        displayFace(faceBlank)
        #utime.sleep(1)
        
        utime.sleep(1)
 
    if detect != True:    
        start =90
        stop = 130
        step = 5
        moveHead(start, stop, step)
        utime.sleep(1)
        
        start =130
        stop = 90
        step = -5
        moveHead(start, stop, step)
        utime.sleep(1)
        
        start =90
        stop = 50
        step = -5
        moveHead(start, stop, step)
        utime.sleep(1)
        
        start = 50
        stop = 90
        step = 5
        moveHead(start, stop, step)
        utime.sleep(1)
 
    print("****end*****")
