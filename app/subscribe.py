# Import SDK packages
import gpiozero
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
from time import sleep
from datetime import datetime
from twilio.rest import Client

# Dont think we'll use this, but keeping just in case
# from rpi_lcd import LCD

import time
import sys

# Token for telegram bot
#my_bot_token = 'bot_key'

# Twilio Token and Information
account_sid = "AC6f95ac61f26e8dbdaa75f51f9bf8b264"
auth_token = "cfda9623873bff4f87df1137c268c7dc"
client = Client(account_sid, auth_token)

# enter the phone number you have enter in twillio
my_hp = "+14102590304"
twilio_hp = "+14439735074"

# Define the variables to be used
led = gpiozero.LED(21)
bz = gpiozero.Buzzer(26)
# lcd = LCD()


# To turn on sensors
def sensor_on(): 
    led.blink()
    bz.on()
    # lcd.text("Alarm is on.", 1)
    sms = "Alarm triggered."
    # lcd.text("SMS Sent.", 2)

    message = client.api.account.messages.create(to=my_hp, from_=twilio_hp, body=sms)

    time.sleep(2)
    # lcd.clear()
    return message


# To turn off sensors
def sensor_off():
    led.off()
    bz.off()
    # lcd.text("Alarm is off.", 1)
    sms = "Alarm is turned off"
    # lcd.clear()
    message = client.api.account.messages.create(to=my_hp, from_=twilio_hp, body=sms)


# Telegram Bot
#def respond_to_msg(msg):
#    chat_id = msg['chat']['id']
#    command = msg['text']

#    print('Got command: {}'.format(command))

#    if command == 'Sensoroff':
#        bot.sendMessage(chat_id, sensor_off())


#bot = telepot.Bot(my_bot_token)
#bot.message_loop(respond_to_msg)
print('Listening for RPi commands...')


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
