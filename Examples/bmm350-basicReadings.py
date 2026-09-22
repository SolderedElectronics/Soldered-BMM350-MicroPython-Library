# FILE: bmm350-basicReadings.py
# AUTHOR: Soldered Electronics
# BRIEF: Reads compensated magnetometer and temperature data from the BMM350
#        sensor over I2C
# WORKS WITH: BMM350 Geomagnetic Sensor breakout: www.solde.red/333359
# LAST UPDATED: 2026-09-22

from bmm350 import BMM350, BMM350_OK
from machine import I2C, Pin
import time

# Change these to match how your board wires I2C
i2c = I2C(0, scl=Pin(9), sda=Pin(8))
sensor = BMM350(i2c)

if sensor.status != BMM350_OK:
    raise Exception("Failed to initialize BMM350: " + sensor.status_string())

print("BMM350 connected!")

while True:
    if sensor.get_sensor_data() == BMM350_OK:
        print(
            "X: {:.2f} uT\tY: {:.2f} uT\tZ: {:.2f} uT\tTemperature: {:.2f} degC".format(
                sensor.data.mag_x, sensor.data.mag_y, sensor.data.mag_z, sensor.data.temperature
            )
        )
    else:
        print("Failed to read sensor data:", sensor.status_string())

    time.sleep_ms(100)
