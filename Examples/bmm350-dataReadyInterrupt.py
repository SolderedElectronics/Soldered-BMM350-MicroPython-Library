# FILE: bmm350-dataReadyInterrupt.py
# AUTHOR: Soldered Electronics
# BRIEF: Uses the BMM350's physical interrupt pin to know when a new
#        magnetometer reading is ready, instead of polling the interrupt
#        status register
# WORKS WITH: BMM350 Geomagnetic Sensor breakout: www.solde.red/333359
# LAST UPDATED: 2026-09-22

from bmm350 import BMM350, BMM350_OK, BMM350_PULSED, BMM350_ACTIVE_HIGH, BMM350_INTR_PUSH_PULL
from machine import I2C, Pin

# Hardware setup: connect the breakout board's INT pin to INT_PIN below
INT_PIN = 5

data_ready = False


def int_callback(pin):
    global data_ready
    data_ready = True


# Change these to match how your board wires I2C
i2c = I2C(0, scl=Pin(9), sda=Pin(8))
sensor = BMM350(i2c)

if sensor.status != BMM350_OK:
    raise Exception("Failed to initialize BMM350: " + sensor.status_string())

print("BMM350 connected!")

# Configure the interrupt pin as push/pull, active high, pulsed and mapped
# to the physical pin
sensor.configure_interrupt(BMM350_PULSED, BMM350_ACTIVE_HIGH, BMM350_INTR_PUSH_PULL, True)

# Enable the data-ready interrupt
sensor.enable_interrupt(True)

interrupt_pin = Pin(INT_PIN, Pin.IN)
interrupt_pin.irq(trigger=Pin.IRQ_RISING, handler=int_callback)

while True:
    if data_ready:
        data_ready = False
        status = sensor.get_interrupt_status()
        if status:
            if sensor.get_sensor_data() == BMM350_OK:
                print(
                    "X: {:.2f} uT\tY: {:.2f} uT\tZ: {:.2f} uT".format(
                        sensor.data.mag_x, sensor.data.mag_y, sensor.data.mag_z
                    )
                )
            else:
                print("Failed to read sensor data:", sensor.status_string())
