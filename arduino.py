import serial
import requests

arduino = serial.Serial("COM6", baudrate=9600, timeout=1)

url = "http://127.0.0.1:5000/fire_event"

while True:
    data = arduino.readline().decode().strip()
    if data:  # If Arduino sends "FIRE"
        payload = {"status": data}
        response = requests.post(url, json=payload)
        print("Sent:", payload, "Response:", response.text)