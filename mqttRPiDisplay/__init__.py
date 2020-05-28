import paho.mqtt.client as mqtt
import asyncio

DEFAULT_DISPLAY = "/sys/class/backlight/rpi_backlight/brightness"


class RPiDisplay:
    def __init__(self, name: str, host: str, port: int = 1883, display: str = DEFAULT_DISPLAY, state_topic: str = None, cmd_topic: str = None):
        self.display = display
        self.name = name
        self.track = False
        self.brightness = self.brightness()

        self.mqtt = mqtt.Client(self.name)
        self.mqtt.connect(host, port=port)

        if state_topic is not None:
            self.state_topic = f"displays/{self.name}/state/brightness"
        else:
            self.state_topic = state_topic

        if cmd_topic is not None:
            self.cmd_topic = f"displays/{self.name}/cmd/brightness"
        else:
            self.cmd_topic = cmd_topic

    def get_brightness(self) -> int:
        with open(self.display, 'r') as fh:
            brightness = fh.read()

        brightness = int(brightness)

        return brightness

    def set_brightness(self, brightness: int) -> None:
        with open(self.display, 'w') as fh:
            fh.write(str(brightness))

        self.brightness = brightness

    def publish_brightness(self, brightness: int) -> None:
        self.mqtt.publish(self.state_topic, brightness, retain=True)

        self.brightness = brightness

    def subscribe_brightness(self) -> None:
        def handle_message(_client, _userdata, message) -> None:
            brightness = message.payload.decode("utf-8")
            self.set_brightness(brightness)

        self.mqtt.subscribe(self.cmd_topic)
        self.mqtt.on_message = handle_message

    async def track_brightness(self) -> None:
        while self.track:
            brightness = self.get_brightness()
            if brightness != self.brightness:
                self.publish_brightness(brightness)

            await asyncio.sleep(5)

    def start(self) -> None:
        self.track = True

        loop = asyncio.get_event_loop()
        loop.create_task(self.track_brightness())
        loop.run_forever()

    def stop(self) -> None:
        self.track = False
        loop = asyncio.get_event_loop()
        loop.stop()
