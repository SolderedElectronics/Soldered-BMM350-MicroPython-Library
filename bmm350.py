# FILE: bmm350.py
# AUTHOR: Soldered Electronics
# BRIEF: MicroPython driver for the Bosch BMM350 geomagnetic sensor,
#        register-level ported from Bosch's BMM350_SensorAPI (bmm350.c/
#        bmm350_defs.h, BSD-3-Clause), matching the Soldered BMM350
#        Arduino/ESP-IDF libraries
# LAST UPDATED: 2026-09-22

from machine import I2C, Pin
from os import uname
import time

# I2C addresses (set by the state of the ADSEL pin)
BMM350_I2C_ADSEL_SET_LOW = 0x14
BMM350_I2C_ADSEL_SET_HIGH = 0x15

# Chip identifier and command bytes
BMM350_CHIP_ID = 0x33
BMM350_CMD_SOFTRESET = 0xB6

# Return codes of the driver
BMM350_OK = 0
BMM350_E_NULL_PTR = -1
BMM350_E_COM_FAIL = -2
BMM350_E_DEV_NOT_FOUND = -3
BMM350_E_INVALID_CONFIG = -4
BMM350_E_SELF_TEST_INVALID_AXIS = -8
BMM350_E_OTP_BOOT = -9
BMM350_E_OTP_PAGE_RD = -10
BMM350_E_OTP_PAGE_PRG = -11
BMM350_E_OTP_SIGN = -12
BMM350_E_OTP_INV_CMD = -13
BMM350_E_OTP_UNDEFINED = -14
BMM350_E_ALL_AXIS_DISABLED = -15
BMM350_E_PMU_CMD_VALUE = -16

# Aggregated result of check_status()
BMM350_ERROR = -1

# Enable / disable
BMM350_DISABLE = 0
BMM350_ENABLE = 1

# Power mode configurations (PMU_CMD values)
BMM350_SUSPEND_MODE = 0x00
BMM350_NORMAL_MODE = 0x01
_BMM350_PMU_CMD_UPD_OAE = 0x02
BMM350_FORCED_MODE = 0x03
BMM350_FORCED_MODE_FAST = 0x04
_BMM350_PMU_CMD_FGR = 0x05
_BMM350_PMU_CMD_BR = 0x07
_BMM350_PMU_CMD_BR_FAST = 0x08

# Output data rate configurations
BMM350_DATA_RATE_400HZ = 0x2
BMM350_DATA_RATE_200HZ = 0x3
BMM350_DATA_RATE_100HZ = 0x4
BMM350_DATA_RATE_50HZ = 0x5
BMM350_DATA_RATE_25HZ = 0x6
BMM350_DATA_RATE_12_5HZ = 0x7
BMM350_DATA_RATE_6_25HZ = 0x8
BMM350_DATA_RATE_3_125HZ = 0x9
BMM350_DATA_RATE_1_5625HZ = 0xA

# Performance / averaging settings
BMM350_NO_AVERAGING = 0x0
BMM350_AVERAGING_2 = 0x1
BMM350_AVERAGING_4 = 0x2
BMM350_AVERAGING_8 = 0x3

# Interrupt pin mode
BMM350_PULSED = 0
BMM350_LATCHED = 1

# Interrupt pin polarity
BMM350_ACTIVE_LOW = 0
BMM350_ACTIVE_HIGH = 1

# Interrupt pin drive
BMM350_INTR_OPEN_DRAIN = 0
BMM350_INTR_PUSH_PULL = 1

# Register map
BMM350_REG_CHIP_ID = 0x00
BMM350_REG_PMU_CMD_AGGR_SET = 0x04
BMM350_REG_PMU_CMD_AXIS_EN = 0x05
BMM350_REG_PMU_CMD = 0x06
BMM350_REG_PMU_CMD_STATUS_0 = 0x07
BMM350_REG_INT_CTRL = 0x2E
BMM350_REG_INT_STATUS = 0x30
BMM350_REG_MAG_X_XLSB = 0x31
BMM350_REG_OTP_CMD_REG = 0x50
BMM350_REG_OTP_DATA_MSB_REG = 0x52
BMM350_REG_OTP_DATA_LSB_REG = 0x53
BMM350_REG_OTP_STATUS_REG = 0x55
BMM350_REG_TMR_SELFTEST_USER = 0x60
BMM350_REG_CMD = 0x7E

# Bit masks / positions used to pack and unpack the registers above. Named to
# match the Bosch driver's macros (bmm350_defs.h) so they can be cross-checked
# against it directly.
_BMM350_ODR_MSK = 0xF
_BMM350_AVG_MSK = 0x30
_BMM350_AVG_POS = 4
_BMM350_EN_X_MSK = 0x01
_BMM350_EN_Y_MSK = 0x02
_BMM350_EN_Y_POS = 1
_BMM350_EN_Z_MSK = 0x04
_BMM350_EN_Z_POS = 2
_BMM350_EN_XYZ_MSK = 0x7
_BMM350_INT_MODE_MSK = 0x1
_BMM350_INT_POL_MSK = 0x2
_BMM350_INT_POL_POS = 1
_BMM350_INT_OD_MSK = 0x4
_BMM350_INT_OD_POS = 2
_BMM350_INT_OUTPUT_EN_MSK = 0x8
_BMM350_INT_OUTPUT_EN_POS = 3
_BMM350_DRDY_DATA_REG_EN_MSK = 0x80
_BMM350_DRDY_DATA_REG_EN_POS = 7
_BMM350_DRDY_DATA_REG_MSK = 0x4
_BMM350_DRDY_DATA_REG_POS = 2
_BMM350_PMU_CMD_BUSY_MSK = 0x1
_BMM350_ODR_OVWR_MSK = 0x2
_BMM350_ODR_OVWR_POS = 1
_BMM350_AVG_OVWR_MSK = 0x4
_BMM350_AVG_OVWR_POS = 2
_BMM350_PWR_MODE_IS_NORMAL_MSK = 0x8
_BMM350_PWR_MODE_IS_NORMAL_POS = 3
_BMM350_CMD_IS_ILLEGAL_MSK = 0x10
_BMM350_CMD_IS_ILLEGAL_POS = 4
_BMM350_PMU_CMD_VALUE_MSK = 0xE0
_BMM350_PMU_CMD_VALUE_POS = 5
_BMM350_ST_IGEN_EN_MSK = 0x1
_BMM350_ST_N_MSK = 0x2
_BMM350_ST_N_POS = 1
_BMM350_ST_P_MSK = 0x4
_BMM350_ST_P_POS = 2
_BMM350_IST_EN_X_MSK = 0x8
_BMM350_IST_EN_X_POS = 3
_BMM350_IST_EN_Y_MSK = 0x10
_BMM350_IST_EN_Y_POS = 4

# PMU_CMD_STATUS_0.pmu_cmd_value echoes back which PMU command last completed
_BMM350_PMU_CMD_STATUS_0_FGR = 0x05
_BMM350_PMU_CMD_STATUS_0_BR = 0x07
_BMM350_PMU_CMD_STATUS_0_FM_FAST = 0x04
_BMM350_PMU_CMD_STATUS_0_BR_FAST = 0x07  # same encoded value as _BR, per the vendor header

# Self-test command bytes written to TMR_SELFTEST_USER
_BMM350_SELF_TEST_NEG_X = 0x0B
_BMM350_SELF_TEST_POS_X = 0x0D
_BMM350_SELF_TEST_NEG_Y = 0x13
_BMM350_SELF_TEST_POS_Y = 0x15

# OTP command/status bytes
_BMM350_OTP_CMD_DIR_READ = 0x20
_BMM350_OTP_CMD_PWR_OFF_OTP = 0x80
_BMM350_OTP_WORD_ADDR_MSK = 0x1F
_BMM350_OTP_STATUS_ERROR_MSK = 0xE0
_BMM350_OTP_STATUS_NO_ERROR = 0x00
_BMM350_OTP_STATUS_BOOT_ERR = 0x20
_BMM350_OTP_STATUS_PAGE_RD_ERR = 0x40
_BMM350_OTP_STATUS_PAGE_PRG_ERR = 0x60
_BMM350_OTP_STATUS_SIGN_ERR = 0x80
_BMM350_OTP_STATUS_INV_CMD_ERR = 0xA0
_BMM350_OTP_STATUS_CMD_DONE = 0x01
_BMM350_OTP_DATA_LENGTH = 32

# 2 dummy bytes precede every I2C read (datasheet section 9.2.3): an n byte
# read must actually pull n+2 bytes, with the first 2 discarded
_BMM350_DUMMY_BYTES = 2
_BMM350_MAG_TEMP_DATA_LEN = 12

# Delays required by the sensor, in microseconds
_BMM350_DELAY_US_START_UP_TIME_FROM_POR = 3000
_BMM350_DELAY_US_SOFT_RESET = 24000
_BMM350_DELAY_US_GOTO_SUSPEND = 6000
_BMM350_DELAY_US_UPD_OAE = 1000
_BMM350_DELAY_US_BR = 14000
_BMM350_DELAY_US_FGR = 18000
_BMM350_DELAY_US_SUSPEND_TO_NORMAL = 38000
# Suspend -> forced mode delay, indexed by averaging setting (0..3)
_BMM350_DELAY_US_SUS_TO_FORCED = (15000, 17000, 20000, 28000)
# Suspend -> forced mode fast delay, indexed by averaging setting (0..3)
_BMM350_DELAY_US_SUS_TO_FORCED_FAST = (4000, 5000, 9000, 16000)

# Text descriptions of the status codes, used by status_string()
_STATUS_STRINGS = {
    BMM350_OK: "",
    BMM350_E_NULL_PTR: "Null pointer",
    BMM350_E_COM_FAIL: "Communication failure",
    BMM350_E_DEV_NOT_FOUND: "Sensor not found",
    BMM350_E_INVALID_CONFIG: "Invalid configuration",
    BMM350_E_SELF_TEST_INVALID_AXIS: "Invalid self-test axis",
    BMM350_E_OTP_BOOT: "OTP boot failure",
    BMM350_E_OTP_PAGE_RD: "OTP page read failure",
    BMM350_E_OTP_PAGE_PRG: "OTP page program failure",
    BMM350_E_OTP_SIGN: "OTP sign failure",
    BMM350_E_OTP_INV_CMD: "Invalid OTP command",
    BMM350_E_OTP_UNDEFINED: "Undefined OTP error",
    BMM350_E_ALL_AXIS_DISABLED: "All axes disabled",
    BMM350_E_PMU_CMD_VALUE: "Invalid PMU command value",
}


def _fix_sign(inval, number_of_bits):
    """Port of bmm350.c's static fix_sign() (line ~1465): sign-extend an
    n-bit two's complement value packed into an unsigned int."""
    power = {8: 128, 12: 2048, 16: 32768, 21: 1048576, 24: 8388608}.get(number_of_bits, 0)
    retval = inval
    if retval >= power:
        retval -= power * 2
    return retval


class BMM350Data:
    """One magnetometer/temperature reading."""

    def __init__(self):
        self.mag_x = 0.0
        self.mag_y = 0.0
        self.mag_z = 0.0
        self.temperature = 0.0

    def __repr__(self):
        return "BMM350Data(mag_x={:.2f}, mag_y={:.2f}, mag_z={:.2f}, temperature={:.2f})".format(
            self.mag_x, self.mag_y, self.mag_z, self.temperature
        )


class BMM350:
    """
    MicroPython driver for the Soldered BMM350 breakout board, I2C only.

    The sensor is initialized by the constructor, which raises an exception
    when it cannot be reached. Every other method stores its result in the
    status attribute instead of raising, the same way the Arduino/ESP-IDF
    libraries do, so check_status() and status_string() report what went
    wrong.
    """

    def __init__(self, i2c=None, address=BMM350_I2C_ADSEL_SET_LOW):
        """
        Initialize the BMM350.

        :param i2c: Initialized I2C object, auto-detected on known boards
        :param address: I2C address, BMM350_I2C_ADSEL_SET_LOW (0x14) by
                         default (matches ADSEL tied low on this breakout)
        """
        if i2c is not None:
            self.i2c = i2c
        else:
            if uname().sysname in (
                "esp32",
                "esp8266",
                "Soldered Dasduino CONNECTPLUS",
            ):
                self.i2c = I2C(0, scl=Pin(22), sda=Pin(21))
            else:
                raise Exception("Board not recognized, enter I2C pins manually")

        self.address = address
        self.status = BMM350_OK
        self.intf_rslt = BMM350_OK
        self.chip_id = 0
        self.data = BMM350Data()

        # Mirrors dev->axis_en in the vendor driver: bit 0/1/2 = X/Y/Z enabled
        self._axis_en = _BMM350_EN_XYZ_MSK

        # Magnetometer compensation coefficients, populated from OTP by
        # _otp_dump_after_boot_raw() during init (see _update_mag_off_sens_raw())
        self._mag_comp = None

        self._init_sensor()

    # ------------------------------------------------------------------
    # Bus access
    # ------------------------------------------------------------------

    def _get_regs(self, reg_addr, length):
        """
        Read a block of registers, raises OSError on a bus failure.

        Port of bmm350_get_regs() (bmm350.c line ~347): the sensor always
        prepends 2 dummy bytes to a read, so length+2 bytes are requested
        and the first 2 are discarded.
        """
        data = self.i2c.readfrom_mem(self.address, reg_addr, length + _BMM350_DUMMY_BYTES)
        self.intf_rslt = BMM350_OK
        return data[_BMM350_DUMMY_BYTES:]

    def _set_regs(self, reg_addr, reg_data):
        """
        Write a block of registers, raises OSError on a bus failure.

        Every call site in the vendor driver writes exactly 1 byte (verified
        against all ~26 bmm350_set_regs() call sites in bmm350.c) even though
        the datasheet describes multi-byte I2C writes as needing explicit
        address/data pairs (not a plain auto-incrementing burst) -- so this
        never needs to implement that multi-byte case.
        """
        self.i2c.writeto_mem(self.address, reg_addr, bytes(reg_data))
        self.intf_rslt = BMM350_OK

    def read_reg(self, reg_addr, length=1):
        """
        Read one or more registers.

        :param reg_addr: Address of the first register
        :param length: Number of bytes to read
        :return: An integer for a single byte, bytes otherwise, None on error
        """
        try:
            data = self._get_regs(reg_addr, length)
            self.status = BMM350_OK
            return data[0] if length == 1 else data
        except OSError:
            self.intf_rslt = BMM350_E_COM_FAIL
            self.status = BMM350_E_COM_FAIL
            return None

    def write_reg(self, reg_addr, reg_data):
        """
        Write one register.

        :param reg_addr: Address of the register
        :param reg_data: Single byte value to write
        """
        try:
            self._set_regs(reg_addr, [reg_data])
            self.status = BMM350_OK
        except OSError:
            self.intf_rslt = BMM350_E_COM_FAIL
            self.status = BMM350_E_COM_FAIL

    # ------------------------------------------------------------------
    # OTP readout and magnetometer compensation coefficients
    #
    # The BMM350 stores its factory calibration (offset/sensitivity/
    # temperature-coefficient/cross-axis terms) in one-time-programmable
    # memory, read out word by word through a command/status handshake on
    # boot. Port of read_otp_word() (line ~1510) and
    # otp_dump_after_boot()/update_mag_off_sens() (lines ~1590-1844, float
    # branch only -- BMM350_USE_FIXED_POINT is not defined by default).
    # ------------------------------------------------------------------

    def _read_otp_word_raw(self, addr):
        """
        Direct port of bmm350.c's static read_otp_word(). Returns
        (value, status) instead of raising on an OTP protocol error, to
        mirror otp_dump_after_boot()'s loop (see below).
        """
        otp_cmd = _BMM350_OTP_CMD_DIR_READ | (addr & _BMM350_OTP_WORD_ADDR_MSK)
        self._set_regs(BMM350_REG_OTP_CMD_REG, [otp_cmd])

        otp_status = 0
        while True:
            time.sleep_us(300)
            otp_status = self._get_regs(BMM350_REG_OTP_STATUS_REG, 1)[0]
            otp_err = otp_status & _BMM350_OTP_STATUS_ERROR_MSK
            if otp_err != _BMM350_OTP_STATUS_NO_ERROR:
                status = {
                    _BMM350_OTP_STATUS_BOOT_ERR: BMM350_E_OTP_BOOT,
                    _BMM350_OTP_STATUS_PAGE_RD_ERR: BMM350_E_OTP_PAGE_RD,
                    _BMM350_OTP_STATUS_PAGE_PRG_ERR: BMM350_E_OTP_PAGE_PRG,
                    _BMM350_OTP_STATUS_SIGN_ERR: BMM350_E_OTP_SIGN,
                    _BMM350_OTP_STATUS_INV_CMD_ERR: BMM350_E_OTP_INV_CMD,
                }.get(otp_err, BMM350_E_OTP_UNDEFINED)
                return 0, status
            if otp_status & _BMM350_OTP_STATUS_CMD_DONE:
                break

        msb = self._get_regs(BMM350_REG_OTP_DATA_MSB_REG, 1)[0]
        lsb = self._get_regs(BMM350_REG_OTP_DATA_LSB_REG, 1)[0]
        return ((msb << 8) | lsb) & 0xFFFF, BMM350_OK

    def _otp_dump_after_boot_raw(self):
        """
        Direct port of bmm350.c's static otp_dump_after_boot(). Note: like
        the vendor driver, this does not stop early on a per-word OTP error
        -- it reads all 32 words regardless and only the status of the last
        one ends up mattering. That is the vendor's own (odd but harmless in
        practice) behavior, preserved here rather than "fixed".
        """
        otp_data = [0] * _BMM350_OTP_DATA_LENGTH
        status = BMM350_OK
        for indx in range(_BMM350_OTP_DATA_LENGTH):
            otp_data[indx], status = self._read_otp_word_raw(indx)

        self._update_mag_off_sens_raw(otp_data)
        return status

    def _update_mag_off_sens_raw(self, otp_data):
        """
        Direct port of bmm350.c's static update_mag_off_sens(), float branch
        only (line ~1590). Each 16 bit OTP word packs two 8 bit (or one 12/16
        bit) calibration fields; addresses below are the OTP word indices
        used by the vendor driver (BMM350_MAG_OFFSET_X etc in bmm350_defs.h).
        """
        off_x_lsb_msb = otp_data[0x0E] & 0x0FFF
        off_y_lsb_msb = ((otp_data[0x0E] & 0xF000) >> 4) + (otp_data[0x0F] & 0x00FF)
        off_z_lsb_msb = (otp_data[0x0F] & 0x0F00) + (otp_data[0x10] & 0x00FF)
        t_off = otp_data[0x0D] & 0x00FF

        sens_x = (otp_data[0x10] & 0xFF00) >> 8
        sens_y = otp_data[0x11] & 0x00FF
        sens_z = (otp_data[0x11] & 0xFF00) >> 8
        t_sens = (otp_data[0x0D] & 0xFF00) >> 8

        tco_x = otp_data[0x12] & 0x00FF
        tco_y = otp_data[0x13] & 0x00FF
        tco_z = otp_data[0x14] & 0x00FF

        tcs_x = (otp_data[0x12] & 0xFF00) >> 8
        tcs_y = (otp_data[0x13] & 0xFF00) >> 8
        tcs_z = (otp_data[0x14] & 0xFF00) >> 8

        cross_x_y = otp_data[0x15] & 0x00FF
        cross_y_x = (otp_data[0x15] & 0xFF00) >> 8
        cross_z_x = otp_data[0x16] & 0x00FF
        cross_z_y = (otp_data[0x16] & 0xFF00) >> 8

        self._mag_comp = {
            "offset_x": _fix_sign(off_x_lsb_msb, 12),
            "offset_y": _fix_sign(off_y_lsb_msb, 12),
            "offset_z": _fix_sign(off_z_lsb_msb, 12),
            "t_offs": _fix_sign(t_off, 8) / 5.0,
            "sens_x": _fix_sign(sens_x, 8) / 256.0,
            "sens_y": _fix_sign(sens_y, 8) / 256.0,
            "sens_z": _fix_sign(sens_z, 8) / 256.0,
            "t_sens": _fix_sign(t_sens, 8) / 512.0,
            "tco_x": _fix_sign(tco_x, 8) / 32.0,
            "tco_y": _fix_sign(tco_y, 8) / 32.0,
            "tco_z": _fix_sign(tco_z, 8) / 32.0,
            "tcs_x": _fix_sign(tcs_x, 8) / 16384.0,
            "tcs_y": _fix_sign(tcs_y, 8) / 16384.0,
            "tcs_z": _fix_sign(tcs_z, 8) / 16384.0,
            "t0": (_fix_sign(otp_data[0x18], 16) / 512.0) + 23.0,
            "cross_x_y": _fix_sign(cross_x_y, 8) / 800.0,
            "cross_y_x": _fix_sign(cross_y_x, 8) / 800.0,
            "cross_z_x": _fix_sign(cross_z_x, 8) / 800.0,
            "cross_z_y": _fix_sign(cross_z_y, 8) / 800.0,
        }

    # ------------------------------------------------------------------
    # Initialization
    #
    # bmm350_init() (line ~224) and bmm350_soft_reset() (line ~416) share
    # most of their body but aren't identical: init's own soft-reset step is
    # just cmd+delay, while the public soft_reset() (and init(), separately,
    # right after the OTP dump) additionally power off the OTP and run a
    # magnetic reset. Kept as two helpers below to mirror that.
    # ------------------------------------------------------------------

    def _soft_reset_cmd_raw(self):
        """The minimal soft-reset step used inside init(): cmd + delay only."""
        self._set_regs(BMM350_REG_CMD, [BMM350_CMD_SOFTRESET])
        time.sleep_us(_BMM350_DELAY_US_SOFT_RESET)

    def _power_off_otp_and_magnetic_reset_raw(self):
        self._set_regs(BMM350_REG_OTP_CMD_REG, [_BMM350_OTP_CMD_PWR_OFF_OTP])
        return self._magnetic_reset_and_wait_raw()

    def _init_sensor(self):
        """Direct port of bmm350_init()."""
        try:
            time.sleep_us(_BMM350_DELAY_US_START_UP_TIME_FROM_POR)
            self._soft_reset_cmd_raw()

            self.chip_id = self._get_regs(BMM350_REG_CHIP_ID, 1)[0]
        except OSError:
            self.intf_rslt = BMM350_E_COM_FAIL
            self.status = BMM350_E_COM_FAIL
            raise Exception(
                "BMM350 not responding on address 0x{:02x}".format(self.address)
            )

        if self.chip_id != BMM350_CHIP_ID:
            self.status = BMM350_E_DEV_NOT_FOUND
            raise Exception(
                "BMM350 not found, chip ID 0x{:02x} was read instead of 0x{:02x}".format(
                    self.chip_id, BMM350_CHIP_ID
                )
            )

        try:
            otp_status = self._otp_dump_after_boot_raw()
            if otp_status != BMM350_OK:
                self.status = otp_status
                raise Exception("BMM350 OTP readout failed: " + self.status_string())

            reset_status = self._power_off_otp_and_magnetic_reset_raw()
            if reset_status != BMM350_OK:
                self.status = reset_status
                raise Exception("BMM350 magnetic reset failed: " + self.status_string())

            self.set_odr_performance(BMM350_DATA_RATE_100HZ, BMM350_AVERAGING_4)
            if self.status != BMM350_OK:
                raise Exception("BMM350 default configuration failed: " + self.status_string())

            self.enable_axes(True, True, True)
            if self.status != BMM350_OK:
                raise Exception("BMM350 default configuration failed: " + self.status_string())

            self.set_mode(BMM350_NORMAL_MODE)
            if self.status != BMM350_OK:
                raise Exception("BMM350 default configuration failed: " + self.status_string())
        except OSError:
            self.intf_rslt = BMM350_E_COM_FAIL
            self.status = BMM350_E_COM_FAIL
            raise Exception(
                "BMM350 not responding on address 0x{:02x}".format(self.address)
            )

    def soft_reset(self):
        """Soft reset the sensor, the configuration is lost."""
        try:
            self._soft_reset_cmd_raw()
            self.status = self._power_off_otp_and_magnetic_reset_raw()
        except OSError:
            self.intf_rslt = BMM350_E_COM_FAIL
            self.status = BMM350_E_COM_FAIL

    # ------------------------------------------------------------------
    # Power mode
    #
    # Port of bmm350_set_powermode() (line ~555, the public API) and its
    # static helper set_powermode() (line ~2060). A reset/mode change can
    # only be triggered from suspend, so the public function suspends first
    # if the sensor is currently in normal mode or mid-ODR-update.
    # ------------------------------------------------------------------

    def _set_powermode_raw(self, mode):
        """Direct port of bmm350.c's static set_powermode()."""
        self._set_regs(BMM350_REG_PMU_CMD, [mode])

        avg_reg = self._get_regs(BMM350_REG_PMU_CMD_AGGR_SET, 1)[0]
        avg = (avg_reg & _BMM350_AVG_MSK) >> _BMM350_AVG_POS

        delay_us = 0
        if mode == BMM350_NORMAL_MODE:
            delay_us = _BMM350_DELAY_US_SUSPEND_TO_NORMAL
        elif mode == BMM350_FORCED_MODE:
            delay_us = _BMM350_DELAY_US_SUS_TO_FORCED[avg]
        elif mode == BMM350_FORCED_MODE_FAST:
            delay_us = _BMM350_DELAY_US_SUS_TO_FORCED_FAST[avg]

        if delay_us:
            time.sleep_us(delay_us)

    def _set_mode_full_raw(self, mode):
        """Direct port of bmm350.c's public bmm350_set_powermode()."""
        last_pwr_mode = self._get_regs(BMM350_REG_PMU_CMD, 1)[0]

        if last_pwr_mode > _BMM350_PMU_CMD_BR_FAST:
            raise ValueError("sensor reported an invalid PMU command state")

        if last_pwr_mode in (BMM350_NORMAL_MODE, _BMM350_PMU_CMD_UPD_OAE):
            self._set_regs(BMM350_REG_PMU_CMD, [BMM350_SUSPEND_MODE])
            time.sleep_us(_BMM350_DELAY_US_GOTO_SUSPEND)

        self._set_powermode_raw(mode)

    def set_mode(self, mode):
        """
        Set the power mode.

        :param mode: BMM350_SUSPEND_MODE, BMM350_NORMAL_MODE,
                      BMM350_FORCED_MODE or BMM350_FORCED_MODE_FAST
        """
        try:
            self._set_mode_full_raw(mode)
            self.status = BMM350_OK
        except ValueError:
            self.status = BMM350_E_INVALID_CONFIG
        except OSError:
            self.intf_rslt = BMM350_E_COM_FAIL
            self.status = BMM350_E_COM_FAIL

    # ------------------------------------------------------------------
    # Magnetic reset
    #
    # Port of bmm350_magnetic_reset_and_wait() (line ~887): issues a Bit
    # Reset (BR) then a Flux Guide Reset (FGR) while in suspend mode, each
    # followed by a fixed delay and a check that the command actually
    # completed. Getting the delay wrong here (too short) makes the status
    # check read a stale PMU_CMD_STATUS_0 value and fail with
    # BMM350_E_PMU_CMD_VALUE -- time.sleep_us() is a real busy/blocking wait
    # in MicroPython so this doesn't have the tick-quantization hazard the
    # ESP-IDF port had to fix.
    # ------------------------------------------------------------------

    def _get_pmu_cmd_status_0_raw(self):
        """Direct port of bmm350.c's bmm350_get_pmu_cmd_status_0()."""
        reg_data = self._get_regs(BMM350_REG_PMU_CMD_STATUS_0, 1)[0]
        return {
            "pmu_cmd_busy": reg_data & _BMM350_PMU_CMD_BUSY_MSK,
            "odr_ovwr": (reg_data & _BMM350_ODR_OVWR_MSK) >> _BMM350_ODR_OVWR_POS,
            "avr_ovwr": (reg_data & _BMM350_AVG_OVWR_MSK) >> _BMM350_AVG_OVWR_POS,
            "pwr_mode_is_normal": (reg_data & _BMM350_PWR_MODE_IS_NORMAL_MSK) >> _BMM350_PWR_MODE_IS_NORMAL_POS,
            "cmd_is_illegal": (reg_data & _BMM350_CMD_IS_ILLEGAL_MSK) >> _BMM350_CMD_IS_ILLEGAL_POS,
            "pmu_cmd_value": (reg_data & _BMM350_PMU_CMD_VALUE_MSK) >> _BMM350_PMU_CMD_VALUE_POS,
        }

    def _magnetic_reset_and_wait_raw(self):
        """
        Direct port of bmm350.c's bmm350_magnetic_reset_and_wait(). Returns
        BMM350_OK or BMM350_E_PMU_CMD_VALUE instead of raising, so callers
        can fold it into their own status-code handling (matching how the
        rest of this driver reports errors -- only OSError from a real bus
        fault is raised).
        """
        status0 = self._get_pmu_cmd_status_0_raw()
        restore_normal = status0["pwr_mode_is_normal"] == BMM350_ENABLE

        if restore_normal:
            # Reset can only be triggered in suspend
            self._set_mode_full_raw(BMM350_SUSPEND_MODE)

        self._set_regs(BMM350_REG_PMU_CMD, [_BMM350_PMU_CMD_BR])
        time.sleep_us(_BMM350_DELAY_US_BR)

        status0 = self._get_pmu_cmd_status_0_raw()
        if status0["pmu_cmd_value"] != _BMM350_PMU_CMD_STATUS_0_BR:
            return BMM350_E_PMU_CMD_VALUE

        self._set_regs(BMM350_REG_PMU_CMD, [_BMM350_PMU_CMD_FGR])
        time.sleep_us(_BMM350_DELAY_US_FGR)

        status0 = self._get_pmu_cmd_status_0_raw()
        if status0["pmu_cmd_value"] != _BMM350_PMU_CMD_STATUS_0_FGR:
            return BMM350_E_PMU_CMD_VALUE

        if restore_normal:
            self._set_mode_full_raw(BMM350_NORMAL_MODE)

        return BMM350_OK

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def set_odr_performance(self, odr, avg):
        """
        Set output data rate and averaging (performance) configuration.

        Direct port of bmm350_set_odr_performance() (line ~604): averaging
        is silently reduced when it's too high for the chosen ODR, matching
        the vendor driver exactly (not an error condition).

        :param odr: One of the BMM350_DATA_RATE_* constants
        :param avg: One of BMM350_NO_AVERAGING, BMM350_AVERAGING_2,
                    BMM350_AVERAGING_4 or BMM350_AVERAGING_8
        """
        try:
            avg_fix = avg
            if odr == BMM350_DATA_RATE_400HZ and avg >= BMM350_AVERAGING_2:
                avg_fix = BMM350_NO_AVERAGING
            elif odr == BMM350_DATA_RATE_200HZ and avg >= BMM350_AVERAGING_4:
                avg_fix = BMM350_AVERAGING_2
            elif odr == BMM350_DATA_RATE_100HZ and avg >= BMM350_AVERAGING_8:
                avg_fix = BMM350_AVERAGING_4

            reg_data = odr & _BMM350_ODR_MSK
            reg_data = (reg_data & ~_BMM350_AVG_MSK & 0xFF) | ((avg_fix << _BMM350_AVG_POS) & _BMM350_AVG_MSK)
            self._set_regs(BMM350_REG_PMU_CMD_AGGR_SET, [reg_data])

            self._set_regs(BMM350_REG_PMU_CMD, [_BMM350_PMU_CMD_UPD_OAE])
            time.sleep_us(_BMM350_DELAY_US_UPD_OAE)

            self.status = BMM350_OK
        except OSError:
            self.intf_rslt = BMM350_E_COM_FAIL
            self.status = BMM350_E_COM_FAIL

    def enable_axes(self, en_x, en_y, en_z):
        """
        Enable or disable individual measurement axes.

        :param en_x: Enable the X axis
        :param en_y: Enable the Y axis
        :param en_z: Enable the Z axis
        """
        if not (en_x or en_y or en_z):
            self._axis_en = BMM350_DISABLE
            self.status = BMM350_E_ALL_AXIS_DISABLED
            return

        try:
            data = BMM350_ENABLE if en_x else BMM350_DISABLE
            data = (data & ~_BMM350_EN_Y_MSK & 0xFF) | (
                ((BMM350_ENABLE if en_y else BMM350_DISABLE) << _BMM350_EN_Y_POS) & _BMM350_EN_Y_MSK
            )
            data = (data & ~_BMM350_EN_Z_MSK & 0xFF) | (
                ((BMM350_ENABLE if en_z else BMM350_DISABLE) << _BMM350_EN_Z_POS) & _BMM350_EN_Z_MSK
            )

            self._set_regs(BMM350_REG_PMU_CMD_AXIS_EN, [data])
            self._axis_en = data
            self.status = BMM350_OK
        except OSError:
            self.intf_rslt = BMM350_E_COM_FAIL
            self.status = BMM350_E_COM_FAIL

    # ------------------------------------------------------------------
    # Interrupt
    # ------------------------------------------------------------------

    def get_interrupt_status(self):
        """
        Get the data-ready interrupt status.

        Useful whether you're polling it directly or checking it after the
        sensor's physical interrupt pin fires.

        :return: Data-ready interrupt status (0 or 1), None on error
        """
        try:
            reg_data = self._get_regs(BMM350_REG_INT_STATUS, 1)[0]
            self.status = BMM350_OK
            return (reg_data & _BMM350_DRDY_DATA_REG_MSK) >> _BMM350_DRDY_DATA_REG_POS
        except OSError:
            self.intf_rslt = BMM350_E_COM_FAIL
            self.status = BMM350_E_COM_FAIL
            return None

    def enable_interrupt(self, enable):
        """
        Enable or disable the data-ready interrupt.

        :param enable: True to enable, False to disable
        """
        try:
            reg_data = self._get_regs(BMM350_REG_INT_CTRL, 1)[0]
            reg_data = (reg_data & ~_BMM350_DRDY_DATA_REG_EN_MSK & 0xFF) | (
                ((BMM350_ENABLE if enable else BMM350_DISABLE) << _BMM350_DRDY_DATA_REG_EN_POS)
                & _BMM350_DRDY_DATA_REG_EN_MSK
            )
            self._set_regs(BMM350_REG_INT_CTRL, [reg_data])
            self.status = BMM350_OK
        except OSError:
            self.intf_rslt = BMM350_E_COM_FAIL
            self.status = BMM350_E_COM_FAIL

    def configure_interrupt(self, latching, polarity, drive, map_to_pin):
        """
        Configure the behavior of the sensor's physical interrupt pin.

        Does not enable the interrupt itself, see enable_interrupt().

        :param latching: BMM350_PULSED or BMM350_LATCHED
        :param polarity: BMM350_ACTIVE_LOW or BMM350_ACTIVE_HIGH
        :param drive: BMM350_INTR_OPEN_DRAIN or BMM350_INTR_PUSH_PULL
        :param map_to_pin: True to map the data-ready interrupt to the
                            physical pin, False to unmap it
        """
        try:
            reg_data = self._get_regs(BMM350_REG_INT_CTRL, 1)[0]
            reg_data = (reg_data & ~_BMM350_INT_MODE_MSK & 0xFF) | (latching & _BMM350_INT_MODE_MSK)
            reg_data = (reg_data & ~_BMM350_INT_POL_MSK & 0xFF) | (
                (polarity << _BMM350_INT_POL_POS) & _BMM350_INT_POL_MSK
            )
            reg_data = (reg_data & ~_BMM350_INT_OD_MSK & 0xFF) | ((drive << _BMM350_INT_OD_POS) & _BMM350_INT_OD_MSK)
            reg_data = (reg_data & ~_BMM350_INT_OUTPUT_EN_MSK & 0xFF) | (
                ((BMM350_ENABLE if map_to_pin else BMM350_DISABLE) << _BMM350_INT_OUTPUT_EN_POS)
                & _BMM350_INT_OUTPUT_EN_MSK
            )
            self._set_regs(BMM350_REG_INT_CTRL, [reg_data])
            self.status = BMM350_OK
        except OSError:
            self.intf_rslt = BMM350_E_COM_FAIL
            self.status = BMM350_E_COM_FAIL

    # ------------------------------------------------------------------
    # Reading out measurements
    #
    # Port of bmm350_read_uncomp_mag_temp_data() (line ~768),
    # read_out_raw_data()/update_default_coefiecents() (lines ~1747-1811,
    # float branch) and bmm350_get_compensated_mag_xyz_temp_data() (line
    # ~1102, float branch).
    # ------------------------------------------------------------------

    def _read_uncomp_mag_temp_data_raw(self):
        """Direct port of bmm350_read_uncomp_mag_temp_data()."""
        mag_data = self._get_regs(BMM350_REG_MAG_X_XLSB, _BMM350_MAG_TEMP_DATA_LEN)

        raw_mag_x = mag_data[0] | (mag_data[1] << 8) | (mag_data[2] << 16)
        raw_mag_y = mag_data[3] | (mag_data[4] << 8) | (mag_data[5] << 16)
        raw_mag_z = mag_data[6] | (mag_data[7] << 8) | (mag_data[8] << 16)
        raw_temp = mag_data[9] | (mag_data[10] << 8) | (mag_data[11] << 16)

        raw_x = 0 if (self._axis_en & _BMM350_EN_X_MSK) == BMM350_DISABLE else _fix_sign(raw_mag_x, 24)
        raw_y = 0 if (self._axis_en & _BMM350_EN_Y_MSK) == BMM350_DISABLE else _fix_sign(raw_mag_y, 24)
        raw_z = 0 if (self._axis_en & _BMM350_EN_Z_MSK) == BMM350_DISABLE else _fix_sign(raw_mag_z, 24)
        raw_t = _fix_sign(raw_temp, 24)

        return raw_x, raw_y, raw_z, raw_t

    def _read_out_raw_data_raw(self):
        """
        Direct port of read_out_raw_data() (float branch) and
        update_default_coefiecents(): converts raw LSB counts to
        microtesla/degC using the sensor's fixed analog front-end gains
        (these constants are not per-device OTP data, they're the same for
        every BMM350).
        """
        raw_x, raw_y, raw_z, raw_t = self._read_uncomp_mag_temp_data_raw()

        bxy_sens = 14.55
        bz_sens = 9.0
        temp_sens = 0.00204
        ina_xy_gain_trgt = 19.46
        ina_z_gain_trgt = 31.0
        adc_gain = 1 / 1.5
        lut_gain = 0.714607238769531
        power = 1000000.0 / 1048576.0

        lsb_to_ut_xy = power / (bxy_sens * ina_xy_gain_trgt * adc_gain * lut_gain)
        lsb_to_ut_z = power / (bz_sens * ina_z_gain_trgt * adc_gain * lut_gain)
        lsb_to_degc_t = 1 / (temp_sens * adc_gain * lut_gain * 1048576)

        out_x = raw_x * lsb_to_ut_xy
        out_y = raw_y * lsb_to_ut_xy
        out_z = raw_z * lsb_to_ut_z
        out_t = (raw_t * lsb_to_degc_t) - 25.49

        return [out_x, out_y, out_z, out_t]

    def get_sensor_data(self):
        """
        Read a new compensated magnetometer/temperature measurement into
        self.data. Direct port of bmm350_get_compensated_mag_xyz_temp_data()
        (float branch).

        :return: BMM350_OK on success, an error code otherwise
        """
        try:
            out = self._read_out_raw_data_raw()
            comp = self._mag_comp

            out[3] = (1 + comp["t_sens"]) * out[3] + comp["t_offs"]

            offset = (comp["offset_x"], comp["offset_y"], comp["offset_z"])
            sens = (comp["sens_x"], comp["sens_y"], comp["sens_z"])
            tco = (comp["tco_x"], comp["tco_y"], comp["tco_z"])
            tcs = (comp["tcs_x"], comp["tcs_y"], comp["tcs_z"])

            for i in range(3):
                out[i] *= 1 + sens[i]
                out[i] += offset[i]
                out[i] += tco[i] * (out[3] - comp["t0"])
                out[i] /= 1 + tcs[i] * (out[3] - comp["t0"])

            cross_x_y = comp["cross_x_y"]
            cross_y_x = comp["cross_y_x"]
            cross_z_x = comp["cross_z_x"]
            cross_z_y = comp["cross_z_y"]
            denom = 1 - cross_y_x * cross_x_y

            cr_ax_comp_x = (out[0] - cross_x_y * out[1]) / denom
            cr_ax_comp_y = (out[1] - cross_y_x * out[0]) / denom
            cr_ax_comp_z = out[2] + (
                out[0] * (cross_y_x * cross_z_y - cross_z_x) - out[1] * (cross_z_y - cross_x_y * cross_z_x)
            ) / denom

            self.data.mag_x = 0.0 if (self._axis_en & _BMM350_EN_X_MSK) == BMM350_DISABLE else cr_ax_comp_x
            self.data.mag_y = 0.0 if (self._axis_en & _BMM350_EN_Y_MSK) == BMM350_DISABLE else cr_ax_comp_y
            self.data.mag_z = 0.0 if (self._axis_en & _BMM350_EN_Z_MSK) == BMM350_DISABLE else cr_ax_comp_z
            self.data.temperature = out[3]

            self.status = BMM350_OK
        except OSError:
            self.intf_rslt = BMM350_E_COM_FAIL
            self.status = BMM350_E_COM_FAIL

        return self.status

    # ------------------------------------------------------------------
    # Self-test
    #
    # Port of self_test_entry_config()/self_test_xy_axis()/self_test_config()
    # (lines ~1845-2055) and bmm350_perform_self_test() (line ~1212). The
    # self-test drives an internal ~130uT field on X then Y and measures the
    # resulting field difference; per the datasheet section 5.1.6, a channel
    # is considered working if its reported value is >= 130uT.
    # ------------------------------------------------------------------

    def _set_tmr_selftest_user_raw(self, st_igen_en, st_n_en, st_p_en, ist_x_en, ist_y_en):
        """Direct port of bmm350_set_tmr_selftest_user()."""
        reg_data = self._get_regs(BMM350_REG_TMR_SELFTEST_USER, 1)[0]
        reg_data = (reg_data & ~_BMM350_ST_IGEN_EN_MSK & 0xFF) | (st_igen_en & _BMM350_ST_IGEN_EN_MSK)
        reg_data = (reg_data & ~_BMM350_ST_N_MSK & 0xFF) | ((st_n_en << _BMM350_ST_N_POS) & _BMM350_ST_N_MSK)
        reg_data = (reg_data & ~_BMM350_ST_P_MSK & 0xFF) | ((st_p_en << _BMM350_ST_P_POS) & _BMM350_ST_P_MSK)
        reg_data = (reg_data & ~_BMM350_IST_EN_X_MSK & 0xFF) | (
            (ist_x_en << _BMM350_IST_EN_X_POS) & _BMM350_IST_EN_X_MSK
        )
        reg_data = (reg_data & ~_BMM350_IST_EN_Y_MSK & 0xFF) | (
            (ist_y_en << _BMM350_IST_EN_Y_POS) & _BMM350_IST_EN_Y_MSK
        )
        self._set_regs(BMM350_REG_TMR_SELFTEST_USER, [reg_data])

    def _self_test_entry_config_raw(self):
        """Direct port of bmm350.c's static self_test_entry_config()."""
        self._set_regs(BMM350_REG_PMU_CMD, [BMM350_SUSPEND_MODE])
        time.sleep_us(30000)

        self.set_odr_performance(BMM350_DATA_RATE_100HZ, BMM350_AVERAGING_2)
        self.enable_axes(True, True, True)

        self._set_regs(BMM350_REG_PMU_CMD, [_BMM350_PMU_CMD_FGR])
        time.sleep_us(30000)

        status0 = self._get_pmu_cmd_status_0_raw()
        if status0["pmu_cmd_value"] == _BMM350_PMU_CMD_STATUS_0_FGR:
            self._set_regs(BMM350_REG_PMU_CMD, [_BMM350_PMU_CMD_BR_FAST])
            time.sleep_us(4000)

        status0 = self._get_pmu_cmd_status_0_raw()
        if status0["pmu_cmd_value"] == _BMM350_PMU_CMD_STATUS_0_BR_FAST:
            self._set_regs(BMM350_REG_PMU_CMD, [BMM350_FORCED_MODE_FAST])
            time.sleep_us(16000)

            status0 = self._get_pmu_cmd_status_0_raw()
            if status0["pmu_cmd_value"] == _BMM350_PMU_CMD_STATUS_0_FM_FAST:
                time.sleep_us(10)

    def _self_test_config_raw(self, st_cmd, out_data):
        """Direct port of bmm350.c's static self_test_config()."""
        self._set_regs(BMM350_REG_TMR_SELFTEST_USER, [st_cmd])
        time.sleep_us(1000)

        self._set_regs(BMM350_REG_PMU_CMD, [BMM350_FORCED_MODE_FAST])
        time.sleep_us(6000)

        status0 = self._get_pmu_cmd_status_0_raw()
        if status0["pmu_cmd_value"] != _BMM350_PMU_CMD_STATUS_0_FM_FAST:
            return

        out_ust = self._read_out_raw_data_raw()

        if st_cmd == _BMM350_SELF_TEST_POS_X:
            out_data["out_ust_xh"] = out_ust[0]
        elif st_cmd == _BMM350_SELF_TEST_NEG_X:
            out_data["out_ust_xl"] = out_ust[0]
        elif st_cmd == _BMM350_SELF_TEST_POS_Y:
            out_data["out_ust_yh"] = out_ust[1]
        elif st_cmd == _BMM350_SELF_TEST_NEG_Y:
            out_data["out_ust_yl"] = out_ust[1]
            out_data["out_ust_x"] = out_data["out_ust_xh"] - out_data["out_ust_xl"]
            out_data["out_ust_y"] = out_data["out_ust_yh"] - out_data["out_ust_yl"]

    def perform_self_test(self):
        """
        Run the sensor's built-in self-test.

        :return: dict with keys out_ust_x, out_ust_y (field difference in
                 microtesla on each axis; >= 130.0 is a pass per the
                 datasheet), None on error
        """
        try:
            last_pwr_mode = self._get_regs(BMM350_REG_PMU_CMD, 1)[0]

            self._self_test_entry_config_raw()

            out_data = {"out_ust_xh": 0.0, "out_ust_xl": 0.0, "out_ust_yh": 0.0, "out_ust_yl": 0.0}
            self._self_test_config_raw(_BMM350_SELF_TEST_POS_X, out_data)
            self._self_test_config_raw(_BMM350_SELF_TEST_NEG_X, out_data)
            self._self_test_config_raw(_BMM350_SELF_TEST_POS_Y, out_data)
            self._self_test_config_raw(_BMM350_SELF_TEST_NEG_Y, out_data)

            self._set_tmr_selftest_user_raw(BMM350_DISABLE, BMM350_DISABLE, BMM350_DISABLE, BMM350_DISABLE,
                                            BMM350_DISABLE)
            time.sleep_us(1000)

            if last_pwr_mode == BMM350_NORMAL_MODE:
                self._set_mode_full_raw(BMM350_NORMAL_MODE)

            self.status = BMM350_OK
            return {"out_ust_x": out_data["out_ust_x"], "out_ust_y": out_data["out_ust_y"]}
        except OSError:
            self.intf_rslt = BMM350_E_COM_FAIL
            self.status = BMM350_E_COM_FAIL
            return None

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def check_status(self):
        """
        Check whether the last call failed.

        :return: BMM350_ERROR if the last call failed, BMM350_OK otherwise
        """
        if self.status < BMM350_OK:
            return BMM350_ERROR

        return BMM350_OK

    def status_string(self):
        """
        Get a short description of the current status code.

        :return: Description of the status, an empty string when it is OK
        """
        return _STATUS_STRINGS.get(self.status, "Undefined error code")
