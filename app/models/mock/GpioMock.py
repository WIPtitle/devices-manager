class GpioMock:
    HIGH = 1
    LOW = 0
    IN = 0
    OUT = 1
    BCM = 11
    BOARD = 10
    PUD_UP = 1
    PUD_DOWN = -1
    PUD_OFF = 0

    def __init__(self):
        pass

    @staticmethod
    def setmode(mode):
        pass

    @staticmethod
    def setup(channel, state, pull_up_down=None):
        pass

    @staticmethod
    def output(channel, state):
        pass

    @staticmethod
    def input(channel):
        return GpioMock.LOW

    @staticmethod
    def cleanup(channel=None):
        pass
