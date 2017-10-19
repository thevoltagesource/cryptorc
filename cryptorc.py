import requests
import json
import time
import RPIO
from RPIO import PWM
from collections import deque
import Adafruit_CharLCD as LCD

# Bitcoin / Crypto Roller Coaster
# Python code for Raspberry Pi
#
# Code By Jacob Southard (aka /u/sandlewoodshire)
# email: jacob@odyssey.ws
#   
# Feel free to use this code in your own project.
# If you use this in a project send me a note and let me know it was useful.
# If you build off this code and decide to share your work, I would appreciate some credit in the comments.
#
# This code would not be possible if it wasn't for:
#     Adafruit's CharLCD Library https://github.com/adafruit/Adafruit_Python_CharLCD
#     Chris Hager's RPIO (v2 beta) Library https://github.com/metachris/RPIO
#  
# Hopefully you picked on on the fact you need to download and install these libraries for this to work.


# coins we want to track
coins = ['BTC', 'LTC']

# I am a Texan so USD it is.
fiat = 'USD'

# % change trigger values
tup90 = 1.00
tup67 = .90
tup45 = .55
tup22 = .10
tdown22 = -.10
tdown45 = -.55
tdown67 = -.90
tdown90 = -1.00

# Servo positions <- Adjust these for your servo
up90 = 2300
up67 = 2040
up45 = 1770
up22 = 1510
level = 1350
down22 = 1160
down45 = 960
down67 = 760
down90 = 570

# Time between price checks (in minutes)
waittime = 5
# The time delta (in minutes) we are using to calculate the change percentage
deltatime = 60
# how many prices to store.  Must be at least equal to deltatime / checktime
depth = 15
# Array position of currently displayed coin
tracking = 0

# Dictionary of our deques
history = {}
# Dictionary of current price percentage delta
percentdelta = {}

# Button pressed boolean
buttonpressed = False

# URL parameters for retreiving crypto prices
cryptourl="https://min-api.cryptocompare.com/data/pricemulti"
cryptoparameters = {'fsyms': ','.join(coins), 'tsyms': fiat, 'e': 'Coinbase'}

# LCD pins
lcd_rs        = 25 
lcd_en        = 24
lcd_d4        = 23
lcd_d5        = 17
lcd_d6        = 27
lcd_d7        = 22

# Define LCD column and row size
lcd_columns = 16
lcd_rows    = 2

# Initialize the LCD using the pins above.
lcd = LCD.Adafruit_CharLCD(lcd_rs, lcd_en, lcd_d4, lcd_d5, lcd_d6, lcd_d7,lcd_columns, lcd_rows)
lcd.clear()

# Configure RPIO options
RPIO.setmode(RPIO.BCM)
RPIO.wait_for_interrupts(threaded=True)

# Servo control
cart = PWM.Servo()

def setup():
    # Build Deques
    for coin in coins:
        history[coin] = deque([],depth)
        percentdelta[coin] = 0
    # Set button response
    RPIO.add_interrupt_callback(4, buttonaction, edge='falling', pull_up_down=RPIO.PUD_UP, threaded_callback=True, debounce_timeout_ms=300)
    # Move cart to level position
    cart.set_servo(18,level)

def updatelcd (currency, price, delta):
    print("{} price: {}   {} % change".format(currency, price, delta))
    # Write current price/%change to lcd
    lcd.clear()
    lcd.message("{} Price: {}\n{}% change".format(currency, price, delta))

def updatehistory ():
    # Get current prices
    prices = getprices()
    print(prices)
    # Add prices to history deque
    for coin in coins:
        history[coin].appendleft(prices[coin][fiat])
        if len(history[coin]) < deltatime//waittime :
            past = len(history[coin]) - 1
            if past < 0 :
                past = 0
        else :
            past = (deltatime//waittime) - 1
        pricedelta = history[coin][0] - history[coin][past]
        percentdelta[coin] = round((pricedelta/history[coin][0])*100, 2)
    print(history)
    print(percentdelta)

def movecart () :
    # Get the % change of the current coin
    change = percentdelta[coins[tracking]]
    
    # Figure out which trigger point we are at and set the position
    if change <= tdown22 :
        position = down22
        if change <= tdown45 :
            position = down45
            if change <= tdown67 :
                position = down67
                if change <= tdown90 :
                    position = down90
    elif change >= tup22 :
        position = up22
        if change >= tup45 :
            position = up45
            if change >= tup67 :
                position = up67
                if change >= tup90 :
                    position = up90
    else :
        position = level

    # Move the cart
    cart.set_servo(18, position)

def getprices ():   
    # Call API to get prices - Fails sometimes so we have try/catch in a loop till we get a valid answer
    getresponse = True
    while getresponse:
        try:
            response = requests.get(cryptourl, params=cryptoparameters)
        except:
            print('Connection Failed. Pausing 10 seconds')
            time.sleep(10)
        else:
            getresponse = False
    return response.json()

def buttonaction (pin, value):
    # Threaded callback function
    global buttonpressed
    buttonpressed = True
    print('The buttonn was pressed! Switch the coin!')

# Run Startup Items
setup()

# Main Loop
try:
    while True:

        updatehistory()
        updatelcd(coins[tracking], history[coins[tracking]][0], percentdelta[coins[tracking]])
        movecart()

        updatetime = time.time() + (waittime * 60)
 
        # while we wait for the next
        while time.time() < updatetime:
            if buttonpressed :
                tracking += 1
                if tracking > (len(coins) -1):
                    tracking = 0
                updatelcd(coins[tracking], history[coins[tracking]][0], percentdelta[coins[tracking]])
                movecart()
                buttonpressed = False


        
except KeyboardInterrupt:
    # clean up GPIO if we break out
    cart.stop_servo(18)
    RPIO.cleanup()

# clean up GPIO if we cleanly exit
cart.stop_servo(18)
RPIO.cleanup()
