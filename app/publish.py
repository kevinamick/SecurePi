from flask import Flask, render_template, request, Response
import gevent
import gevent.monkey
from gevent.pywsgi import WSGIServer
import sys
import os
import MySQLdb
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
from time import sleep
from datetime import datetime
import threading
import gpiozero
from azure.storage.blob import BlockBlobService, ContentSettings, PublicAccess
import configparser
app = Flask(__name__)
from picamera import PiCamera

gevent.monkey.patch_all()

config = configparser.ConfigParser()
config.read('config.ini')

global db
global cursor
global running
global block_blob_service


# green led
ledgreen = gpiozero.LED(12)
# red led
ledred = gpiozero.LED(4)
ms = gpiozero.MotionSensor(18, sample_rate=5, queue_len=1)

camera = PiCamera()
PiCamera.CAPTURE_TIMEOUT = 10

# this is our endpoint
host = config['IOT']['host']
rootCAPath = config['IOT']['rootCAPath']
certificatePath = config['IOT']['certificatePath']
privateKeyPath = config['IOT']['privateKeyPath']

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
    print("AWS connected")
except:
    print("Unexpected error:", sys.exc_info()[0], sys.exc_info()[1])


def system_off():
    global running
    running = False
    ledgreen.off()
    ledred.on()
    return "System is turned off!"


def system_on():
    import mysql.connector
    u, pw, h, database = config['Database']['user'], config['Database']['pwd'], config['Database']['host'], config['Database']['db']
    try:
        global running
        running = True
        my_rpi.connect()
        try:
            global block_blob_service
            
            # azure blob connection
            block_blob_service = BlockBlobService(account_name=config['Azure']['blob_name'], account_key=config['Azure']['blob_key']) 
            print("blob connected")
            # Connect to database
            print("in system_on")
            db = mysql.connector.connect(user=u, password=pw, host=h, port=3306, database=database)
            cursor = db.cursor()
            print("Successfully connected to mysql database!")
            ledgreen.on()
            ledred.off()
        except:
            print("Error connecting to mySQL database")
            print(sys.exc_info()[0], sys.exc_info()[1])
            ledred.blink()

        while running: 
            ms.wait_for_motion(timeout=2)
            if ms.motion_detected:
               print("Motion Detected!");
                
               for x in range(0, 1):
                    my_rpi.publish("sensors/motion", 'Motion Detected', 1) 
                    timenow = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    imagename = str(timenow) + '.jpg'
                    dirname = os.path.dirname(__file__)
                    
                    imagepath = os.path.join(dirname,'static/images/' + imagename)
                    
                    #Camera keeps timing out so this is my hacky way of dealing with it
                    try: 
                        camera.capture(imagepath, use_video_port=True)
                    except:
                        print("Timed out waiting for close")
                    finally:
                        camera.close()
                
                    print("Image Name: " + imagename)
                    print(imagepath)
                    block_blob_service.create_blob_from_path('images', imagename, imagepath, content_settings=ContentSettings(content_type='image/jpeg'))
                    print("blob uploaded")
                   
                    #Insert Blob link into MySQL db
                    generator = block_blob_service.list_blobs('images')
                    for blob in generator:
                        if (blob.name == imagename):
                            bloburl = block_blob_service.make_blob_url('images', blob.name)
                            print(bloburl)
                            sql = "INSERT into Image (ImageName, ImagePath) VALUES ('" + imagename + "','" + bloburl + "')"
                            cursor.execute(sql)
                            db.commit()    
                    
                    #Insert Active State into MySQL for History Graph
                    sql = "INSERT into MotionSensor (State) VALUES ('Active')"
                    cursor.execute(sql)
                    db.commit()
                    sleep(1)         
           
    except MySQLdb.Error as e:
        print("sql")
        print(e)
        ledgreen.off()
        ledred.off()
    except KeyboardInterrupt:
        print("Program aborted.") 
        camera.close()
        cursor.close()
        db.close()
        ledgreen.off()
        ledred.off() 
        gpiozero.cleanup()
        sys.exit()
    except:
        print("Unexpected error:", sys.exc_info()[0], sys.exc_info()[1])
        sys.exit()


@app.route("/GetSystem")
def get_system():
    if running:
        response = "Enabled"
    else:
        response = "Disabled"

    return response


@app.route("/System/<status>")
def system(status):
    if status == "Enabled":
        thread = threading.Thread(target=system_on)
        thread.start()
    elif status == "Disabled":
        print("System Turning Off")
        system_off()

    return ""


# Alarm function.
@app.route("/offAlarm")
def off_alarm():
    my_rpi.publish("sensors/motion", 'sensoroff', 1)
    print("sensor off")
    
    return ""


# Set main() to run in the background.
@app.before_first_request
def activate_job():
    def main():
        system_on()

    thread = threading.Thread(target=main)
    thread.start()


@app.route("/")
def home():
    import mysql.connector
    u, pw, h, db = config['Database']['user'], config['Database']['pwd'], config['Database']['host'], config['Database']['db']
    data = []
    print("In Home")
    con = mysql.connector.connect(user=u, password=pw, host=h, port=3306, database=db)
    print("Database successfully connected")
    cur = con.cursor()
    query = "SELECT ImagePath FROM Image ORDER BY Id DESC "
    cur.execute(query)
    for ImagePath, in cur:
        imagepath = format(ImagePath)
        data.append(imagepath)
    return render_template('index.html', data=data)


@app.route("/History")
def chart():
    import mysql.connector
    u, pw, h, db = config['Database']['user'], config['Database']['pwd'], config['Database']['host'], config['Database']['db']
    chartdata = []
    print("In history")
    con = mysql.connector.connect(user=u, password=pw, host=h, database=db)
    print("Database successfully connected")
    cur = con.cursor()
    query = "SELECT Count(State), DATE(DateTime) FROM MotionSensor WHERE State in ('Active') GROUP BY DATE(DateTime) ORDER BY DateTime DESC "
    cur.execute(query)
    for (State, DateTime) in cur:
        d = []
        ts = str(DateTime)
        d.append(State)
        d.append(ts)
        chartdata.append(d)
    return render_template('history.html', chartdata=chartdata)


@app.route("/Setting")
def setting():
    return render_template('setting.html')


if __name__ == '__main__':
    try:
        http_server = WSGIServer(('0.0.0.0', 5000), app)
        http_server.serve_forever()
        app.debug = True

    except KeyboardInterrupt:
        print("System exit")

    except:
        print("Exception")
