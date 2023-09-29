import paho.mqtt.client as mqtt
import RPi.GPIO as GPIO
import json
import os
import time
import sys
import Adafruit_DHT as dht
import Adafruit_MCP3008
from gpiozero import AngularServo
import requests
import smbus
import Adafruit_SSD1306
from PIL import Image, ImageDraw, ImageFont


display = Adafruit_SSD1306.SSD1306_128_64(rst=None)

DEVICE     = 0x23
ONE_TIME_HIGH_RES_MODE_1 = 0x20
bus = smbus.SMBus(1)



servo = AngularServo(22, min_pulse_width=0.0005, max_pulse_width=0.0023)

am = Adafruit_MCP3008.MCP3008(clk = 11, cs = 8, miso = 9, mosi = 10)

flag = True
flag1 = True
flag2 = True

THINGSBOARD_HOST = 'demo.thingsboard.io'
ACCESS_TOKEN = 'yGh3vVrmRLrv0eQHRPtK'


gpio_state = {18: False}
fan_status={27: False}
pump_status={16: False}

pin = 18
pin2 = 27
pin4 = 16
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(pin, GPIO.OUT)
GPIO.setup(pin2, GPIO.OUT)
GPIO.setup(pin4, GPIO.OUT)


def send_message(name, data, device):
    return requests.post(
            "https://api.mailgun.net/v3/sandboxa23eea2d073241058ce1703da7ba11a2.mailgun.org/messages",
            auth=("api", "becd0fee112532e388a257f368b3c942-50f43e91-9541815d"),
            data={"from": "Me <mailgun@becd0fee112532e388a257f368b3c942-50f43e91-9541815d>",
                    "to": ["artaimer00@gmail.com "],
                    "subject": "PKA GreenHouse",
                    "html": "<html> " + name + " is exceeding the threshold: " + data + " <br></br>"
                    + device + " is turned on <br></br> Dashboard PKA-GH to see more:  https://bom.so/dTw4mA</html>" })

# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, rc, *extra_params):
    print('Connected with result code ' + str(rc))    # Subscribing to receive RPC requests
    client.subscribe('v1/devices/me/rpc/request/+')
    # Sending current GPIO status

    client.publish('v1/devices/me/attributes', get_gpio_status(), 1)
    client.publish('v1/devices/me/attributes', get_fan_status(), 1)
    client.publish('v1/devices/me/attributes', get_pump_status(), 1)


# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    
    print(msg.topic+" "+str(msg.payload))
    # Decode JSON request
    data = json.loads(msg.payload)
    # Check request method

    if data['method'] == 'setGpioStatus':
        # Update GPIO status and reply
        set_gpio_status(data['params'])
        client.publish(msg.topic.replace('request', 'response'), get_gpio_status(), 1)
        client.publish('v1/devices/me/attributes', get_gpio_status(), 1)

    elif data['method'] == 'setFanOn':
        set_fan_status(data['params'])
        client.publish(msg.topic.replace('request', 'response'), get_fan_status(), 1)
        client.publish('v1/devices/me/attributes', get_fan_status(), 1)
    elif data['method'] == 'setFanOff':
        set_fan_status(data['params'])
        client.publish(msg.topic.replace('request', 'response'), get_fan_status(), 1)
        client.publish('v1/devices/me/attributes', get_fan_status(), 1)
        
    elif data['method'] == 'setWpumpOff':
        set_pump_status(data['params'])
        client.publish(msg.topic.replace('request', 'response'), get_pump_status(), 1)
        client.publish('v1/devices/me/attributes', get_pump_status(), 1)
    elif data['method'] == 'setWpumpOn':
        set_pump_status(data['params'])
        client.publish(msg.topic.replace('request', 'response'), get_pump_status(), 1)
        client.publish('v1/devices/me/attributes', get_pump_status(), 1)
        
    elif data['method'] == 'setHdoorOff':
        servo.angle= -90
        door_status={22: False}
        client.publish('v1/devices/me/attributes', json.dumps(door_status), 1)
    elif data['method'] == 'setHdoorOn':
        servo.angle= 90
        door_status={22: True}
        client.publish('v1/devices/me/attributes', json.dumps(door_status), 1)
        


def get_gpio_status():
    
    return json.dumps(gpio_state)

def set_gpio_status(status):    
    # Output GPIOs state
    GPIO.output(pin, GPIO.HIGH if status else GPIO.LOW)
    # Update GPIOs state
    gpio_state[18] = status



def get_fan_status():
    return json.dumps(fan_status)
    
def set_fan_status(status):
    GPIO.output(pin2, GPIO.HIGH if status else GPIO.LOW)
    fan_status[27] = status


def get_pump_status():
    return json.dumps(pump_status)

def set_pump_status(status):
    GPIO.output(pin4, GPIO.HIGH if status else GPIO.LOW)
    pump_status[16] = status


def convertToNumber(data):
  result=(data[1] + (256 * data[0])) / 1.2
  return (result)

def readLight(addr=DEVICE):
  data = bus.read_i2c_block_data(addr,ONE_TIME_HIGH_RES_MODE_1)
  return convertToNumber(data)


INTERVAL=2

sensor_data = {'Temperature1': 0, 'Humidity1': 0,'Temperature2': 0, 'Humidity2': 0 }
soil_data = {'Soilmoisture':0 }
lux_data ={'Lux':0}

local_data = {'latitude': 21.01908694793996, 'longitude':105.64920567296556}

next_reading = time.time() 


client = mqtt.Client()
# Register connect callback
client.on_connect = on_connect
# Registed publish message callback
client.on_message = on_message
# Set access token
client.username_pw_set(ACCESS_TOKEN)
# Connect to ThingsBoard using default MQTT port and 60 seconds keepalive interval
client.connect(THINGSBOARD_HOST, 1883, 60)
client.loop_start()

try:
    display.begin()  # initialize graphics library for selected display module
    display.clear()  # clear display buffer
    display.display()  # write display buffer to the physical display
    displayWidth = display.width  # get width of display
    displayHeight = display.height  # get height of display
    font = ImageFont.load_default()  # load and set default font

    while True:
        
        image = Image.new('1', (displayWidth, displayHeight))  # create graphics library image buffer
        draw = ImageDraw.Draw(image)  # create drawing object

        humidity,temperature = dht.read_retry(dht.DHT22, 4)
        humidity = round(humidity, 2)
        temperature = round(temperature, 2)

        humidity2,temperature2 = dht.read_retry(dht.DHT22, 26)
        humidity2 = round(humidity2, 2)
        temperature2 = round(temperature2, 2)

        
        sensor_data['Temperature1'] = temperature
        sensor_data['Humidity1'] = humidity
        
        sensor_data['Temperature2'] = temperature2
        sensor_data['Humidity2'] = humidity2

        # Sending humidity and temperature data to ThingsBoard
        client.publish('v1/devices/me/telemetry', json.dumps(sensor_data), 1)

        client.publish('v1/devices/me/telemetry', json.dumps(local_data), 1)
         
        print(u"TemperatureI: {:g}\u00b0C, HumidityI: {:g}%".format(temperature, humidity))
        print(u"TemperatureO: {:g}\u00b0C, HumidityO: {:g}%".format(temperature2, humidity2))


        if temperature > 32:
         

           data= str(temperature)
           name= "Temperature"
           device="Fan"
           if flag:
              request= send_message(name, data, device)
              print ('Status: '+format(request.status_code))
              print ('Body:'+ format(request.text))
              
              flag = False
           
        else :
           
           flag = True
           
        moisture_value = am.read_adc(0)
        soil_per = int(100-(moisture_value * 100 / 1023))
        print("Recorded moisture value is %s percentage" % soil_per)


        soil_data['Soilmoisture'] = soil_per

        client.publish('v1/devices/me/telemetry', json.dumps(soil_data), 1)

        
        #(950)
        if moisture_value > 850:
           

           data= str(soil_per)
           name= "Soil moisture"
           device="Waterpumps"
           if flag1:
              request= send_message(name, data, device)
              print ('Status: '+format(request.status_code))
              print ('Body:'+ format(request.text))
              
              flag1 = False
         
        elif moisture_value < 350 :
           flag1= True
           

         
        lightLevel=readLight()
        print("Light Level : " + format(lightLevel,'.2f') + " lx")
        lightLevel = round(lightLevel, 2)


        lux_data['Lux'] = lightLevel
        
        client.publish('v1/devices/me/telemetry', json.dumps(lux_data), 1)

        if lightLevel > 9000:
           data= str(lightLevel)
           name= "Light intensity"
           device="Heaven door"
           if flag2:
              request= send_message(name, data, device)
              print ('Status: '+format(request.status_code))
              print ('Body:'+ format(request.text))
              flag2 = False

        else:
           flag2 = True
  
        
            
        draw.text((1, 0), "°C I: "+ str(int(temperature)), fill=225)
        draw.text((1, 10), "°C O: "+ str(int(temperature2)), fill=225)
        draw.text((60, 0), "Hr% I: "+ str(int(humidity)), fill=225)
        draw.text((60, 10), "Hr% O: "+ str(int(humidity2)), fill=225)
        draw.text((30, 20), "W %: "+ str(soil_per), fill=225)
        draw.text((30, 30), "Lx : "+ str(lightLevel), fill=225)
        
   
        display.image(image)  
        display.display()  


        next_reading += INTERVAL
        sleep_time = next_reading-time.time()
        if sleep_time > 0:
            time.sleep(sleep_time)
except KeyboardInterrupt:
    GPIO.cleanup()
    
client.loop_stop()
client.disconnect()
