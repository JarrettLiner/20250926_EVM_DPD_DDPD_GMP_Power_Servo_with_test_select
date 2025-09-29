import logging
from time import time, sleep

logger = logging.getLogger(__name__)

class ET:
    def __init__(self, vsg, et_iterations=10, vsa=None, pm=None):
        logger.info("Initializing Envelope Tracking (ET) - Placeholder")

        self.vsg = vsg
        self.pm = pm
        self.vsa = vsa
        self.et_iterations = et_iterations
        self.logger = logging.getLogger(__name__)

    def configure(self, *args):
        try:
            et_config_start_time = time()
            self.vsg.query("SOURce1:IQ:OUTPut:ANALog:ENVelope:STATe 1; *OPC?")
            self.vsg.query("SOURce1: IQ:OUTPut: ANALog:TYPE DIFF; *OPC?")
            self.vsg.query(f"SOURce1: IQ:OUTPut: ANALog:ENVelope: DELay {0}; *OPC?")
            self.vsg.query("SOURce1:IQ:OUTPut:ANALog:ENVelope:SHAPing:MODE DETR; *OPC?")
            et_config_time = time()-et_config_start_time
            print(f"ET configure time, , {et_config_time:.3f}")
            print("This includes the time to enable ET and set delay and shaping mode")
            return et_config_time
        except Exception as e:
            logger.error(f"ET configuration failed: {str(e)}")
            raise

    def et_delay_evm(self, et_iterations):
        try:
            logger.info("Starting ET shifting EVM - Placeholder")
            et_iterations_start_time = time()
            # setup a loop here for the et delay steps
            self.vsg.query(f"SOURce1: IQ:OUTPut: ANALog:ENVelope: DELay {- 0.000000009}; *OPC?")

            # after the et delay steps, disable et

