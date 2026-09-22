# FILE: bmm350-selfTest.py
# AUTHOR: Soldered Electronics
# BRIEF: Runs the BMM350's built-in self-test. The self-test generates an
#        internal ~130 uT magnetic field on the X and Y channels and reports
#        the resulting field difference; per the datasheet (section 5.1.6),
#        a channel is considered working if its reported value is >= 130 uT.
# WORKS WITH: BMM350 Geomagnetic Sensor breakout: www.solde.red/333359
# LAST UPDATED: 2026-09-22

from bmm350 import BMM350, BMM350_OK
from machine import I2C, Pin

# Minimum self-test field difference to consider a channel passing,
# per the datasheet's self-test section
SELF_TEST_THRESHOLD_UT = 130.0

# Change these to match how your board wires I2C
i2c = I2C(0, scl=Pin(9), sda=Pin(8))
sensor = BMM350(i2c)

if sensor.status != BMM350_OK:
    raise Exception("Failed to initialize BMM350: " + sensor.status_string())

print("BMM350 connected!")

# Run the self-test. The sensor automatically returns to normal mode
# afterwards since the constructor already left it there.
result = sensor.perform_self_test()
if result is not None:
    x_pass = result["out_ust_x"] >= SELF_TEST_THRESHOLD_UT
    y_pass = result["out_ust_y"] >= SELF_TEST_THRESHOLD_UT
    print("X axis field: {:.2f} uT -> {}".format(result["out_ust_x"], "PASS" if x_pass else "FAIL"))
    print("Y axis field: {:.2f} uT -> {}".format(result["out_ust_y"], "PASS" if y_pass else "FAIL"))
else:
    print("Self-test failed to run:", sensor.status_string())
