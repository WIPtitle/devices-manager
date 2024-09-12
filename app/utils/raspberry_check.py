def is_raspberry():
    try:
        import RPi.GPIO as GPIO
        return True
    except RuntimeError:
        return False