from pynq import allocate
from pynq.lib.dma import DMA
import numpy as np

class CmaBufferFactory():
    def __init__(self):
        pass
        
    def make_cma_buf(self, shape, data_type):
        assert shape != [], RuntimeError
        return allocate(shape=shape, dtype=data_type)
    
    def del_cma_buf(self, cma_buf):
        cma_buf.close()

"""
This class hides the details of the CMA buffers and DMA itself.
It is not the fastest way to do things since it makes various
copies of the data before sending and receiving data.

The class could easily be extended to create some CMA buffers
that are created and kept around for direct access to the buffer
contents.

This class can be used with any compatible IP block connected to the DMA.
"""
class SimpleDmaDriver(DMA, CmaBufferFactory):
     # This line is always the same for any driver
    def __init__(self, description):
        # This line is always the same for any driver
        DMA.__init__(self, description=description)
        CmaBufferFactory.__init__(self)
        self.txbuf = []
        self.rxbuf = []
        
    bindto = ['xilinx.com:ip:axi_dma:7.1']
    
    def resize_bufs(self, shape, dtype, which='both'):
        assert which == 'rx' or which == 'tx' or which == 'both', RuntimeError
        assert shape != [], RuntimeError
        if which == 'tx' or which == 'both' :
            if self.txbuf != [] :
                self.del_cma_buf(self.txbuf)
            self.txbuf = self.make_cma_buf(shape, dtype)
        if which == 'rx' or which == 'both' :
            if self.rxbuf != [] :
                self.del_cma_buf(self.rxbuf)
            self.rxbuf = self.make_cma_buf(shape, dtype)

    def send_dma(self, wait=True):
        self.send_cma_buf(self.txbuf, wait)
        
    def rcv_dma(self, wait=True):
        self.rcv_cma_buf(self.rxbuf, wait)
        
    def send_cpy(self, data, wait=True):
        """
        Copy data into DMA buffer and send it, waits for send to complete before returning
        """
        tx_buf = self.make_cma_buf(data.shape, data.dtype)
        tx_buf[0:len(tx_buf)] = data
        self.send_cma_buf(tx_buf, wait)
        self.del_cma_buf(tx_buf)

    def rcv_cpy(self, shape, dtype, wait=True):
        """
        Attempts to read up to max_num words, it waits until the transfer is complete before returning
        """
        rx_buf = self.make_cma_buf(shape, dtype)
        self.rcv_cma_buf(rx_buf, wait)
        data = np.array(rx_buf)
        self.del_cma_buf(rx_buf)
        return data
    
    def rcv_cma_buf(self, cma_only_buf, wait=True):
        """
        Attempts to read up to max_num words, it waits until the transfer is complete before returning
        """
        self.recvchannel.transfer(cma_only_buf)
        if wait == True :
            self.recvchannel.wait()

    def send_cma_buf(self, cma_only_buf, wait=True):
        """
        Copy data into DMA buffer and send it, waits for send to complete before returning
        """
        self.sendchannel.transfer(cma_only_buf)
        if wait == True :
            self.sendchannel.wait()
