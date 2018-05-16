# Import SDK packages
import gpiozero
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
from time import sleep
from datetime import datetime
from twilio.rest import Client
import configparser
import time
import sys

config= configparser.ConfigParser()
config.read('../config.ini')

# Twilio Token and Information
account_sid = config['Twillio']['sid'] 
auth_token = config['Twillio']['token']
client = Client(account_sid, auth_token)

# Twilio Info
my_hp = "+14102590304"
twilio_hp = "+14439735074"

#GPIO config
led = gpiozero.LED(21)
bz = gpiozero.Buzzer(26)

def sensor_on(): 
    led.blink()
    bz.on()
    sms = "Alarm triggered."
    message = client.api.account.messages.create(to=my_hp, from_=twilio_hp, body=sms)
    time.sleep(2)
    
    return message

def sensor_off():
    led.off()
    bz.off()
    sms = "Alarm is turned off"
    message = client.api.account.messages.create(to=my_hp, from_=twilio_hp, body=sms)
    
    return message

# Custom MQTT message callback
def custom_callback(client, userdata, message):
    print("Received a new message: ")
    print(message.payload)
    print("from topic: ")
    print(message.topic)
    print("--------------\n\n")

    if message.payload.decode('utf-8') == 'Motion Detected':
        sensor_on()

    elif message.payload.decode('utf-8') == 'sensoroff':
        sensor_off()
        
print('Listening for RPi commands...')

# This is our endpoint
host = "a82oj25fppijb.iot.us-east-2.amazonaws.com"
rootCAPath = "../rootca.pem"
certificatePath = "../71e8df2fbb-certificate.pem.crt"
privateKeyPath = "../71e8df2fbb-private.pem.key"

try:
    my_rpi = AWSIoTMQTTClient("SecurePi")
    my_rpi.configureEndpoint(host, 8883)
    my_rpi.configureCredentials(rootCAPath, privateKeyPath, certificatePath)

    my_rpi.configureOfflinePublishQueueing(-1)  # Infinite offline Publish queueing
    my_rpi.configureDrainingFrequency(2)  # Draining: 2 Hz
    my_rpi.configureConnectDisconnectTimeout(10)  # 10 sec
    my_rpi.configureMQTTOperationTimeout(5)  # 5 sec

    # Connect and subscribe to AWS IoT
    my_rpi.connect()
except:
    print("Unexpected error:", sys.exc_info()[0], sys.exc_info()[1])

while True:
    my_rpi.subscribe("sensors/motion", 1, custom_callback)
    sleep(5) 
