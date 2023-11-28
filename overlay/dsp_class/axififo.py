from enum import Enum
from pynq import DefaultIP

"""
This class defines mnemonics for FIFO ISR events
"""
class AxiFifoIsrBits(Enum):
    RPURE = 0x80000000
    RPORE = 0x40000000
    RPUE  = 0x20000000
    TPOE  = 0x10000000
    TC    = 0x08000000
    RC    = 0x04000000
    TSE   = 0x02000000
    TRC   = 0x01000000
    RRC   = 0x00800000
    TFPF  = 0x00400000
    TFPE  = 0x00200000
    RFPF  = 0x00100000
    RFPE  = 0x00080000
    
"""
This class manages a Xiinx AXI Streaming Data type FIFO.
It is suitable for use across multiple processes or threads
as along as both RX and TX FIFOs are manipulated seperately.
"""
class FifoStreamDriver(DefaultIP):
    # This line is always the same for any driver
    def __init__(self, description):
        # This line is always the same for any driver
        super().__init__(description=description)
        self._reg_map = self.register_map
        self.isr_masks = AxiFifoIsrBits
        self.data_pkts = []  # Data pulled from hardware lives here

    # The easy way to find the value is to just lookup the .bindto
    # member of the original DefaultIP
    bindto = ['xilinx.com:ip:axi_fifo_mm_s:4.2']
    
    def init_events(self):
        """
        Clear out events and disable external interrupts except for RX packet
        """
        # Clear all pending events
        self.write(self._reg_map.ISR.address, 0xffffffff)
        # Enable RX PKT events, all others off
        self.write(self._reg_map.IER.address, self.isr_masks.RC.value)
        # Use this to see that the FIFO hardware is only initialized once, no matter how many object references
        print('FIFO events initialized') 

    def reset_fifo(self, which):
        """
        Resets FIFOS, set which = 'rx', 'tx', 'both'
        """
        if which == 'tx' :
            self.write(self._reg_map.TDFR.address, 0xa5)
        elif which == 'rx' :
            self.write(self._reg_map.RDFR.address, 0xa5)
        elif which == 'both' :
            self.write(self._reg_map.TDFR.address, 0xa5) # TX 1st to stop traffic into RX
            self.write(self._reg_map.RDFR.address, 0xa5)
        else :
            # Invalid fifo string
            RuntimeError

    def read_num_tx_room(self):
        """
        Reads the number of 32-bit words that the TX FIFO has room for
        """
        return self.read(self._reg_map.TDFV.address)
   
    def read_num_rx_words(self):
        """
        Reads the number of 32-bit words in the RX FIFO yet to be read out
        """
        return self.read(self._reg_map.RDFO.address)

    def send_tx_pkt(self, data, wait_for_room=True):
        """
        Sends a list of integers (32-bit words) into the TX FIFO.
        If wait_for_room is True this will wait until there is room.
        """
        num_tx = len(data)
        if type(data) is bytes :
            num_tx >>= 2  # floors non 4 byte len

        if wait_for_room == True :
            while num_tx > self.read_num_tx_room() :
                pass

        # Writing a zero to hardware might be bad
        if num_tx != 0 :
            if type(data) is bytes :
                self.write(self._reg_map.TDFD.address, data)
            else :
                for i in data:
                    self.write(self._reg_map.TDFD.address, i)
            # This FIFO reg counts bytes
            self.write(self._reg_map.TLR.address, num_tx << 2)
    
    def get_rx_fifo_pkts(self, wait_for_data = False):
        """
        Pulls complete packets worth of data out of the RX FIFO.
        If wait_for_data is set to True it will wait potentially
        forever for an RX packet to arrive.
                
        Future enhancements: TBD should not make this wait forever!
        
        Data from the fifo is stored in this class's buffer rx_data_pkts
        """
        if (wait_for_data == True):
            # Hang out here until data is found
            while (self.read(self._reg_map.RDFO.address) == 0) :
                pass

        # Read until empty
        while (self.read(self._reg_map.RDFO.address) > 0) :
            out_data = []
            num_rx_words = self.read(self._reg_map.RLR.address) >> 2  # Read number of words in packet
            for _ in range(num_rx_words):  # Read entire packet of data out
                out_data.append(self.read(self._reg_map.RDFD.address))

            self.data_pkts.append(out_data)
                
    async def isr_handler(self) :
        """
        Meant to be used to handle interrupt events for AXI Stream FIFOs
        """
        await self.interrupt.wait()
        isr_events = self.read(self._reg_map.ISR.address)
        self.write(self._reg_map.ISR.address, isr_events) # Clear ISR bits (Note: the clear here does depend but in general this is the right place)
        if (isr_events & self.isr_masks.RC.value) != 0 :
            self.get_rx_fifo_pkts()
