import paho.mqtt.client as mqtt
import asyncio
import logging
from time import time

DEFAULT_DISPLAY = "/sys/class/backlight/rpi_backlight/brightness"

_LOG = logging.getLogger(__name__)
X11_EVENTS = ['RawTouchBegin', 'RawButtonPress']
DEFAULT_TOUCH_TIMEOUT = 15
DEFAULT_TOUCH_BRIGHTNESS = 100
DEFAULT_USER = "pi"
DEFAULT_XDISPLAY = ":0"
DEFAULT_PORT = 1883


class RPiDisplay:
    def __init__(self,
                 name: str,
                 host: str,
                 port: int = DEFAULT_PORT,
                 display: str = DEFAULT_DISPLAY,
                 xdisplay: str = DEFAULT_XDISPLAY,
                 xuser: str = DEFAULT_USER,
                 touch_timeout: int = DEFAULT_TOUCH_TIMEOUT,
                 touch_brightness: int = DEFAULT_TOUCH_BRIGHTNESS,
                 state_topic: str = None,
                 cmd_topic: str = None,
                 will_topic: str = None):
        self.name = name
        self.host = host
        self.port = port
        self.display = display
        self.xdisplay = xdisplay
        self.xuser = xuser
        self.touch_timeout = touch_timeout
        self.touch_brightness = touch_brightness

        self.track = False
        self._touched = False
        self._last_changed = time()
        self._max_brightness = 255
        self.brightness = self.get_brightness()
        self._previous_brightness = self.brightness

        if state_topic is None:
            self.state_topic = f"displays/{self.name}/state/brightness"
        else:
            self.state_topic = state_topic

        if cmd_topic is None:
            self.cmd_topic = f"displays/{self.name}/cmd/brightness"
        else:
            self.cmd_topic = cmd_topic

        if will_topic is None:
            self.will_topic = f"displays/{self.name}/status"
        else:
            self.will_topic = will_topic

        self.mqtt = mqtt.Client(self.name)
        self.mqtt.on_connect = self._on_connect
        self.mqtt.on_disconnect = self._on_disconnect
        self.mqtt.will_set(self.will_topic, payload="offline", qos=0, retain=True)

    def _on_connect(self, *_) -> None:
        _LOG.info('Connection to MQTT has been established')
        self.mqtt.publish(self.will_topic, "online", retain=True)
        self._subscribe()

    @staticmethod
    def _on_disconnect(*_) -> None:
        _LOG.info('Connection to MQTT has been disconnected')

    def get_brightness(self) -> int:
        _LOG.debug(f"Getting display brightness: {self.display}")
        with open(self.display, 'r') as fh:
            brightness = fh.read()

        brightness = int(brightness)

        return brightness

    def set_brightness(self, brightness: int, touched: bool = False) -> None:
        # Do not set brightness if from touch event and brightness already set by touch event
        if self._touched and touched:
            _LOG.info("Touch brightness already set, doing nothing")
            return

        if brightness > self._max_brightness:
            brightness = self._max_brightness

        self._previous_brightness = self.brightness

        _LOG.info(f"Setting display brightness: {brightness}")
        with open(self.display, 'w') as fh:
            fh.write(str(brightness))

        self.brightness = brightness
        self._touched = touched
        self._last_changed = time()
        self.publish_brightness(self.brightness)

    def publish_brightness(self, brightness: int) -> None:
        _LOG.info(f"Publishing display brightness: {brightness}")
        self.mqtt.publish(self.state_topic, brightness, retain=True)

        self.brightness = brightness

    async def track_xinput(self) -> None:
        cmd_env = {
            'DISPLAY': self.xdisplay
        }

        cmd = f'sudo -u {self.xuser} DISPLAY={self.xdisplay} xinput test-xi2 --root'
        proc = await asyncio.create_subprocess_shell(cmd,
                                                     stdout=asyncio.subprocess.PIPE,
                                                     stderr=asyncio.subprocess.PIPE,
                                                     env=cmd_env)

        while self.track:
            if proc.returncode is not None:
                error = proc.stderr.readline()
                _LOG.error(f"xinput tracking stopped: {error}")
                break

            line = await proc.stdout.readline()
            line = line.decode('utf-8')

            if not any(x in line for x in X11_EVENTS):
                continue

            self.set_brightness(self.brightness + self.touch_brightness, True)
            _LOG.info("Touch input detected")

    async def timeout_touch_changes(self):
        while self.track:
            touch_age = time() - self._last_changed
            if self._touched and touch_age > self.touch_timeout:
                _LOG.info("Reverting touch brightness")
                self.set_brightness(self._previous_brightness)

            await asyncio.sleep(1)

    async def track_brightness(self) -> None:
        _LOG.info(f"Starting brightness tracking")
        while self.track:
            brightness = self.get_brightness()
            if brightness != self.brightness:
                self.publish_brightness(brightness)

            await asyncio.sleep(5)

        _LOG.info(f"Stopped brightness tracking")

    def _connect(self):
        _LOG.debug(f"Starting connection to MQTT: {self.host}:{self.port}")
        self.mqtt.connect(self.host, port=self.port)
        self.mqtt.loop_start()

    def _disconnect(self):
        _LOG.debug(f"Starting disconnect from MQTT: {self.host}:{self.port}")
        self.mqtt.loop_stop()
        self.mqtt.disconnect()

    def _subscribe(self) -> None:
        def handle_message(_client, _userdata, message) -> None:
            brightness = int(message.payload.decode("utf-8"))
            self.set_brightness(brightness)
            _LOG.debug(f"Received brightness command: {brightness}")

        _LOG.info(f"Subscribing to command topic: {self.cmd_topic}")
        self.mqtt.subscribe(self.cmd_topic)
        self.mqtt.on_message = handle_message

    def _unsubscribe(self):
        _LOG.info(f"Unsubscribing from command topic: {self.cmd_topic}")
        self.mqtt.unsubscribe(self.cmd_topic)

    def start(self) -> None:
        _LOG.info("Starting up...")
        self.track = True
        self._connect()

        loop = asyncio.get_event_loop()
        loop.create_task(self.track_brightness())
        loop.create_task(self.timeout_touch_changes())
        loop.create_task(self.track_xinput())
        loop.run_forever()

    def stop(self) -> None:
        _LOG.info("Stopping...")
        self.track = False
        self._unsubscribe()
        self._disconnect()

        loop = asyncio.get_event_loop()
        loop.stop()
