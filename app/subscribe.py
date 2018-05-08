# Import SDK packages
from gpiozero import LED, Button, Buzzer
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
from time import sleep
from datetime import datetime
from twilio.rest import Client

# Dont think we'll use this, but keeping just in case
# from rpi_lcd import LCD

import time
import telepot
import sys

# Token for telegram bot
my_bot_token = 'bot_key'

# Twilio Token and Information
account_sid = "twillio_id"
auth_token = "twillio_authtoken"
client = Client(account_sid, auth_token)

# enter the phone number you have enter in twillio
my_hp = "+6512345668"
twilio_hp = "+1240468-4002"

# Define the variables to be used
led = LED(21)
bz = Buzzer(26)
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
def respond_to_msg(msg):
    chat_id = msg['chat']['id']
    command = msg['text']

    print('Got command: {}'.format(command))

    if command == 'Sensoroff':
        bot.sendMessage(chat_id, sensor_off())


bot = telepot.Bot(my_bot_token)
bot.message_loop(respond_to_msg)
print('Listening for RPi commands...')


# Custom MQTT message callback
def custom_callback(client, userdata, message):
    print("Received a new message: ")
    print(message.payload)
    print("from topic: ")
    print(message.topic)
    print("--------------\n\n")

    if message.payload == 'Motion Detected':
        sensor_on()

    elif message.payload == 'sensoroff':
        sensor_off()


# This is our endpoint
host = "a82oj25fppijb.iot.us-east-2.amazonaws.com"

# TODO: Need to follow the instructions here: https://docs.aws.amazon.com/iot/latest/developerguide/iot-sdk-setup.html
rootCAPath = "rootca.pem"
certificatePath = "SecurePi.cert.pem"
privateKeyPath = "SecurePi.private.key"

try:
    my_rpi = AWSIoTMQTTClient("SubSecurePi")
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
    # change to correct topic
    sleep(2)
