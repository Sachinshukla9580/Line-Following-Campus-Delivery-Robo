from gpiozero import PWMOutputDevice, DigitalOutputDevice, Button, LED
from picamera2 import Picamera2 
import cv2 
import numpy as np 
import time
import serial
import csv
from luma.core.interface.serial import i2c
from luma.oled.device import sh1106
from luma.core.render import canvas
from PIL import ImageFont 
import os

# Raspberry Pi 5 के लिए GPIO सेटअप
os.system("sudo chmod a+rw /dev/gpiochip0")  # GPIO एक्सेस के लिए परमिशन

# === Motor Setup === 
left_motor_forward = PWMOutputDevice(17) 
left_motor_backward = PWMOutputDevice(27) 
right_motor_forward = PWMOutputDevice(22) 
right_motor_backward = PWMOutputDevice(23)

left_motor2_forward = PWMOutputDevice(24) 
left_motor2_backward = PWMOutputDevice(25) 
right_motor2_forward = PWMOutputDevice(5) 
right_motor2_backward = PWMOutputDevice(6)
 
def stop(): 
    left_motor_forward.value = 0 
    left_motor_backward.value = 0 
    right_motor_forward.value = 0 
    right_motor_backward.value = 0
    
    left_motor2_forward.value = 0 
    left_motor2_backward.value = 0 
    right_motor2_forward.value = 0 
    right_motor2_backward.value = 0  
 
def forward(): 
    left_motor_forward.value = 0.9
    right_motor_forward.value = 0.9
    left_motor_backward.value = 0 
    right_motor_backward.value = 0
    
    left_motor2_forward.value = 0.9 
    left_motor2_backward.value = 0 
    right_motor2_forward.value = 0.9 
    right_motor2_backward.value = 0   
 
def instant_left(): 
    left_motor_forward.value = 0 
    left_motor_backward.value = 0.9
    right_motor_forward.value = 0.9
    right_motor_backward.value = 0
    
    left_motor2_forward.value = 0 
    left_motor2_backward.value = 0.9 
    right_motor2_forward.value = 0.9 
    right_motor2_backward.value = 0   
 
def instant_right(): 
    left_motor_forward.value = 0.9
    left_motor_backward.value = 0 
    right_motor_forward.value = 0 
    right_motor_backward.value = 0.9
    
    left_motor2_forward.value = 0.9 
    left_motor2_backward.value = 0 
    right_motor2_forward.value = 0 
    right_motor2_backward.value = 0.9   
 
# === Color Detection === 
def detect_color(frame): 
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV) 
 
    # Green color (instant left) 
    lower_green = np.array([36, 85, 70]) 
    upper_green = np.array([86, 255, 255]) 
    mask_green = cv2.inRange(hsv, lower_green, upper_green) 
 
    # Red color (instant right) 
    lower_red = np.array([45, 103, 100]) 
    upper_red = np.array([180, 255, 255]) 
    mask_red = cv2.inRange(hsv, lower_red, upper_red) 
 
    if cv2.countNonZero(mask_green) > 500: 
        return "green" 
    elif cv2.countNonZero(mask_red) > 500: 
        return "red" 
    else: 
        return "none" 

# Keypad GPIO Setup - gpiozero का उपयोग करें
KEYPAD_ROWS = [0, 12, 13, 19]
KEYPAD_COLS = [26, 16, 20, 21]

KEYPAD_MAP = [
    ['1', '2', '3', 'A'],
    ['4', '5', '6', 'B'],
    ['7', '8', '9', 'C'],
    ['*', '0', '#', 'D']
]


# Buzzer and LED GPIO Setup - gpiozero का उपयोग करें
BUZZER_PIN = 9
GREEN_LED_PIN = 10
RED_LED_PIN = 11

# Initialize buzzer and LEDs (must be at top-level, not inside a function)
buzzer = LED(BUZZER_PIN)        # Use LED for buzzer (on/off control)
green_led = LED(GREEN_LED_PIN)
red_led = LED(RED_LED_PIN)


# Keypad के लिए gpiozero डिवाइसेज
row_devices = [DigitalOutputDevice(pin) for pin in KEYPAD_ROWS]
col_buttons = [Button(pin, pull_up=False) for pin in KEYPAD_COLS]

# Initialize display
serial = i2c(port=1, address=0x3c)
oled = sh1106(serial, width=128, height=64)

# Load a default font
font = ImageFont.load_default()

def clear_display():
    with canvas(oled) as draw:
        draw.rectangle(oled.bounding_box, outline="black", fill="black")

def default_display_text(line):
    with canvas(oled) as draw:
        draw.text((0, 0), line, font=font, fill="white")

def display_text(line1="", line2="", line3=""):
    with canvas(oled) as draw:
        if line1:
            draw.text((0, 0), line1, font=font, fill="white")
        if line2:
            draw.text((0, 20), line2, font=font, fill="white")
        if line3:
            draw.text((0, 40), line3, font=font, fill="white")
        
def get_key():
    """Scans the keypad and returns the pressed key using gpiozero."""
    for i, row in enumerate(row_devices):
        row.on()  # Set row high
        time.sleep(0.01)  # Short delay for stability
        
        for j, col in enumerate(col_buttons):
            if col.is_active:  # Check if column button is pressed
                time.sleep(0.2)  # Debounce
                row.off()  # Turn off row before returning
                return KEYPAD_MAP[i][j]
                
        row.off()  # Turn off row
    return None

def get_user_input(prompt, max_length):
    """Displays a prompt and gets user input from the keypad."""
    user_input = ""
    while len(user_input) < max_length:
        display_text(prompt, user_input)
        key = get_key()
        if key:
            if key == '#':
                return user_input
            elif key == '*':
                user_input = user_input[:-1] if user_input else ""
            else:
                user_input += key
        time.sleep(0.1)  # Small delay to prevent CPU overuse
    return user_input 

def get_otp_from_csv(order_id, filename='orders.csv'):
    """Gets the OTP for a specific order ID from the CSV file."""
    try:
        with open(filename, mode='r') as infile:
            reader = csv.DictReader(infile)
            for row in reader:
                if row.get('order_id') == order_id:
                    return row.get('otp')
        return None
    except FileNotFoundError:
        print(f"Error: {filename} not found.")
        return None

def verify_otp_process(selected_order):
    """Handles the OTP verification process."""
    order_id = selected_order.get('order_id', 'N/A')
    expected_otp = get_otp_from_csv(order_id)
    
    if not expected_otp:
        display_text("Error:", "OTP not found", "for this order")
        time.sleep(3)
        return False
    
    attempts = 5
    while attempts > 0:
        entered_otp = get_user_input("Enter OTP:", 6)  # Assuming OTP is up to 6 digits
        
        if entered_otp == expected_otp:
            display_text("OTP Verified!", "Pick your order", "")
            green_led.blink(0.2, 0.2, 3)  # Blink green LED 3 times
            buzzer.blink(0.2, 0.2, 3)  # Beep buzzer 3 times
            time.sleep(3)
            return True
        else:
            attempts -= 1
            if attempts > 0:
                display_text(f"Wrong OTP!", f"Attempts left: {attempts}", "Try again")
            else:
                display_text("OTP Failed!", "Contact customer", "care: 7571991816")
                red_led.blink(0.5, 0.5, 5)  # Blink red LED 5 times
                buzzer.blink(0.5, 0.5, 5)  # Beep buzzer 5 times
            time.sleep(2)
    
    return False
           
# === Camera Setup === 
picam2 = Picamera2() 
config = picam2.create_preview_configuration(main={"size": (1280, 720), "format": "RGB888"})
picam2.configure(config)
picam2.start() 
time.sleep(2)

# fetch orders from csv
def read_orders_from_csv(filename='orders.csv'):
    """Reads order data and groups them by destination marker."""
    orders_by_destination = {'green': [], 'red': []}
    try:
        with open(filename, mode='r') as infile:
            reader = csv.DictReader(infile)
            for row in reader:
                marker = row.get('destination_marker')
                if marker in orders_by_destination:
                    orders_by_destination[marker].append(row)
        print(f"Successfully loaded orders from {filename}.")
        return orders_by_destination
    except FileNotFoundError:
        print(f"Error: {filename} not found. Please create it.")
        return None
     
#Code function________________________________________________________________________________________________________________________________________
default_display_text("Delivery BOT on Duty")
 
try: 
    while True: 
        frame = picam2.capture_array() 
        frame = cv2.resize(frame, (960, 720))  # Resize for clearer window 
        roi = frame[480:720, :]  # Bottom part for line tracking 
 
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV) 
        lower_black = np.array([13, 34, 0]) 
        upper_black = np.array([179, 255, 243]) 
        mask_black = cv2.inRange(hsv, lower_black, upper_black) 
         
        M = cv2.moments(mask_black) 
        color = detect_color(roi) 
 
        if color == "green":  
            stop() 
            default_display_text("Location Reached")
            # Buzzer और LED के लिए gpiozero का उपयोग
            for i in range(3):
                buzzer.on()
                time.sleep(0.5)
                buzzer.off()
                time.sleep(0.5)
                
            orders = read_orders_from_csv()    
            def trunc(s, n=18): 
                return str(s)[:n]
                
            if orders and orders.get("green"):
                # Display order list
                order_list = orders["green"]
                current_index = 0
                
                while True:
                    order = order_list[current_index]
                    display_text(
                        f"Order {current_index+1}/{len(order_list)}",
                        f"ID: {trunc(order.get('order_id', 'N/A'))}",
                        "A:Next B:Select"
                    )
                    
                    key = get_key()
                    if key == 'A':
                        current_index = (current_index + 1) % len(order_list)
                    elif key == 'B' or key == '#':
                        selected_order = order
                        break
                    time.sleep(0.1)  # Small delay to prevent CPU overuse
                
                # Start OTP verification process
                verify_otp_process(selected_order)
                
                # After OTP process, continue
                display_text("Resuming", "delivery...", "")
                time.sleep(2)
                
        elif color == "red": 
            stop()
            default_display_text("Location Reached")
            # Buzzer और LED के लिए gpiozero का उपयोग
            for i in range(3):
                buzzer.on()
                time.sleep(0.5)
                buzzer.off()
                time.sleep(0.5)
                
            orders = read_orders_from_csv()    
            def trunc(s, n=18): 
                return str(s)[:n]
                
            if orders and orders.get("red"):
                # Display order list
                order_list = orders["red"]
                current_index = 0
                
                while True:
                    order = order_list[current_index]
                    display_text(
                        f"Order {current_index+1}/{len(order_list)}",
                        f"ID: {trunc(order.get('order_id', 'N/A'))}",
                        "A:Next B:Select"
                    )
                    
                    key = get_key()
                    if key == 'A':
                        current_index = (current_index + 1) % len(order_list)
                    elif key == 'B' or key == '#':
                        selected_order = order
                        break
                    time.sleep(0.1)  # Small delay to prevent CPU overuse
                
                # Start OTP verification process
                verify_otp_process(selected_order)
                
                # After OTP process, continue
                display_text("Resuming", "delivery...", "")
                time.sleep(2)
             
        elif M["m00"] != 0: 
            cx = int(M["m10"] / M["m00"]) 
            cy = int(M["m01"] / M["m00"]) 
 
            # Draw a blue dot at the center of the black line on the full frame 
            cv2.circle(frame, (cx, cy + 480), 5, (255, 0, 0), -1) 
 
            if cx < 350: 
                instant_left() 
            elif cx > 610: 
                instant_right() 
            else: 
                forward() 
        else: 
            time.sleep(1) 
            stop() 
 
        cv2.imshow("Line & Color Tracking", frame) 
        if cv2.waitKey(1) == ord('q'): 
            break 
 
except KeyboardInterrupt: 
    print("Stopped by user.") 
finally: 
    stop() 
    cv2.destroyAllWindows()
    # GPIO cleanup अब आवश्यक नहीं है क्योंकि gpiozero स्वचालित रूप से संसाधनों को मुक्त करता है