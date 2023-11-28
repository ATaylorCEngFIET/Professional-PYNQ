from pynq import DefaultIP
from pynq import Clocks

"""
This is a class that controls Timer0 of a Xilinx AXI timer IP block.
This class requires that you import it first and then load an appropriate
Overlay, one that has an axi_timer in it
"""
class AxiTimerDriver(DefaultIP):
    # This line is always the same for any driver
    def __init__(self, description):
        # This line is always the same for any driver
        super().__init__(description=description)
        self.tr = self.register_map
        self.ctrl_bits = 0x0
        self.max_cnt = 0xffffffff
        # You can add your own stuff here

    # This part must be changed to match whichever IP block is being used
    # This is set correctly for the AXI timer
    bindto = ['xilinx.com:ip:axi_timer:2.0']

    def _set_ctl_reg_bits(self, val):
        self.ctrl_bits |= val
        self.write(self.tr.TCSR0.address, self.ctrl_bits)
    def _clear_ctl_reg_bits(self, val):
        self.ctrl_bits &= ~val
        self.write(self.tr.TCSR0.address, self.ctrl_bits)

    def start_tmr(self):
        """
        Starts the timer's counter
        """
        self._set_ctl_reg_bits(0x00000090)
    def stop_tmr(self):
        """
        Stops the timer's counter
        """
        self._clear_ctl_reg_bits(0x00000080)
    def read_count(self):
        """
        Reads the 32-bit counter register
        """
        return (self.read(self.tr.TCR0.address))
    def time_it(self, t1, t2):
        """
        Does the math to compute the diff in seconds between 2 timer reads
        """
        if (t2 - t1) < 0 :
            return (0x100000000 - t1 + t2) / (1e6 * Clocks.fclk0_mhz)
        else :
            return (t2 - t1) / (1e6 * Clocks.fclk0_mhz)
    def set_interval_ticks(self, ticks):
        """
        The value passed in will set the timer interval and should be subtracted from
        the max_cnt value before setting the TLR0 register value.
        Note: the reload value for up mode is where the Timer starts to count NOT the value it counts up to from zero.
        """
        assert(ticks > 0), RuntimeError
        self._clear_ctl_reg_bits(0x20)
        self.write(self.tr.TLR0.address, self.max_cnt - ((ticks - 1) % (self.max_cnt + 1)))
        self._set_ctl_reg_bits(0x20)
        self._clear_ctl_reg_bits(0x20)
    def set_interval_secs(self, secs):
        """
        This will set the interval to the closest tick count which is always > or = to the requested time
        """
        assert(secs > 0), RuntimeError
        ticks = int(secs * 1e6 * Clocks.fclk0_mhz + .999999999999)
        self.set_interval_ticks(ticks)
    def enable_interrupt(self, enable):
        """
        This class enables timer external timer interrupts when enable=True and disables otherwise
        """
        if enable == True :
            self._set_ctl_reg_bits(0x40)
        else:
            self._clear_ctl_reg_bits(0x40)