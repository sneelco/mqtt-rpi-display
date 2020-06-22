import asyncio
from time import sleep
from unittest import TestCase
from unittest.mock import patch, mock_open, MagicMock

from mqttRPiDisplay import RPiDisplay

TEST_NAME = "test-display"
TEST_HOST = "localtest"
TEST_READ_BRIGHTNESS = "100\n"
TEST_PORT = 8080
TEST_DISPLAY = "test_display"
TEST_XDISPLAY = ":2"
TEST_USER = "test"
TEST_TOUCH_TIMEOUT = 60
TEST_TOUCH_BRIGHTNESS = 1
TEST_STATE_TOPIC = "test/state/topic"
TEST_CMD_TOPIC = "test/cmd/topic"
TEST_WILL_TOPIC = "test/will/topic"


class RPiDisplayTest(TestCase):

    @patch('builtins.open', mock_open(read_data=TEST_READ_BRIGHTNESS))
    @patch('paho.mqtt.client.Client')
    def setUp(self, mock_mqtt):
        mock_client = mock_mqtt.side_effect = MagicMock()
        self.test_instance = RPiDisplay(TEST_NAME, TEST_HOST)
        self.mock_client = mock_client

    def test_init_defaults(self):
        with self.subTest("MQTT Client called"):
            self.assertTrue(self.mock_client.called)

        with self.subTest("MQTT will is set"):
            self.test_instance.mqtt.will_set.assert_called_once_with(self.test_instance.will_topic,
                                                                     payload="offline",
                                                                     qos=0,
                                                                     retain=True)

    @patch('builtins.open', mock_open(read_data=TEST_READ_BRIGHTNESS))
    @patch('paho.mqtt.client.Client')
    def test_init_overrides(self, _):
        test_instance = RPiDisplay(TEST_NAME,
                                   TEST_HOST,
                                   port=TEST_PORT,
                                   display=TEST_DISPLAY,
                                   xdisplay=TEST_XDISPLAY,
                                   xuser=TEST_USER,
                                   touch_timeout=TEST_TOUCH_TIMEOUT,
                                   touch_brightness=TEST_TOUCH_BRIGHTNESS,
                                   state_topic=TEST_STATE_TOPIC,
                                   cmd_topic=TEST_CMD_TOPIC,
                                   will_topic=TEST_WILL_TOPIC)

        with self.subTest("port is overridden"):
            self.assertEqual(test_instance.port, TEST_PORT)

        with self.subTest("display is overridden"):
            self.assertEqual(test_instance.display, TEST_DISPLAY)

        with self.subTest("xdisplay is overridden"):
            self.assertEqual(test_instance.xdisplay, TEST_XDISPLAY)

        with self.subTest("xuser is overridden"):
            self.assertEqual(test_instance.xuser, TEST_USER)

        with self.subTest("touch_timeout is overridden"):
            self.assertEqual(test_instance.touch_timeout, TEST_TOUCH_TIMEOUT)

        with self.subTest("touch_brightness is overridden"):
            self.assertEqual(test_instance.touch_brightness, TEST_TOUCH_BRIGHTNESS)

        with self.subTest("state_topic is overridden"):
            self.assertEqual(test_instance.state_topic, TEST_STATE_TOPIC)

        with self.subTest("cmd_topic is overridden"):
            self.assertEqual(test_instance.cmd_topic, TEST_CMD_TOPIC)

        with self.subTest("will_topic is overridden"):
            self.assertEqual(test_instance.will_topic, TEST_WILL_TOPIC)

    @patch('builtins.open', mock_open(read_data=TEST_READ_BRIGHTNESS))
    def test_get_brightness(self):
        self.assertEqual(self.test_instance.get_brightness(), int(TEST_READ_BRIGHTNESS))

    def test_set_brightness(self):
        with patch('builtins.open', mock_open()) as mock_file:
            self.test_instance.set_brightness(50)
            mock_file().write.assert_called_once_with("50")

            with self.subTest("Do nothing on touch call when previously touched"):
                self.test_instance._touched = True
                self.test_instance.set_brightness(150, True)

                self.assertNotEqual(self.test_instance.brightness, 150)

            with self.subTest("Set to max brightness if brightness is exceeded"):
                self.test_instance.set_brightness(self.test_instance._max_brightness + 1)

                self.assertEqual(self.test_instance.brightness, self.test_instance._max_brightness)

    def test_publish_brightness(self):
        self.test_instance.publish_brightness(200)

        with self.subTest('Published is called'):
            self.test_instance.mqtt.publish.assert_called()

        with self.subTest('Published called with test brightness'):
            self.test_instance.mqtt.publish.assert_called_once_with(self.test_instance.state_topic, 200, retain=True)

        with self.subTest('Instance brightness is set'):
            self.assertEqual(self.test_instance.brightness, 200)

    def test_track_brightness(self):
        self.test_instance.track = True
        self.test_instance.publish_brightness = MagicMock()
        self.test_instance.get_brightness = MagicMock()
        self.test_instance.get_brightness.return_value = 100

        async def test_flow():
            await asyncio.sleep(1)
            self.test_instance.get_brightness.return_value = 50
            await asyncio.sleep(6)
            self.test_instance.track = False

        loop = asyncio.get_event_loop()
        loop.create_task(self.test_instance.track_brightness())
        loop.run_until_complete(test_flow())

        loop.stop()

        self.assertEqual(self.test_instance.publish_brightness.call_count, 1)

    def test_track_xinput(self):
        self.assertTrue(False)

    def test_timeout_touch_changes(self):
        self.assertTrue(False)

    def test_subscribe(self):
        self.test_instance._subscribe()

        with self.subTest("Subscribe is called"):
            self.test_instance.mqtt.subscribe.assert_called()

        with self.subTest("cmd_topic is subscribed"):
            self.test_instance.mqtt.subscribe.assert_called_once_with(self.test_instance.cmd_topic)

        with self.subTest("on_message handler is set"):
            self.assertIsNotNone(self.test_instance.mqtt.on_message)

        with self.subTest("brightness set when message received"):
            class TestClient:
                pass

            class TestUserData:
                pass

            class TestMessage:
                payload = b"100"

            mock_set_brightness = self.test_instance.set_brightness = MagicMock()
            self.test_instance.mqtt.on_message(TestClient, TestUserData, TestMessage)
            mock_set_brightness.assert_called_once_with(100)

    def test_unsubscribe(self):
        self.test_instance._unsubscribe()

        with self.subTest("Unsubscribe is called"):
            self.test_instance.mqtt.unsubscribe.assert_called()

        with self.subTest("cmd_topic is unsubscribed"):
            self.test_instance.mqtt.unsubscribe.assert_called_once_with(self.test_instance.cmd_topic)

    def test_connect(self):
        self.test_instance._connect()

        with self.subTest("MQTT Client Connect is Called"):
            self.test_instance.mqtt.connect.assert_called()

        with self.subTest("MQTT Client Connect is Called with Host"):
            self.test_instance.mqtt.connect.assert_called_once_with(self.test_instance.host,
                                                                    port=self.test_instance.port)

        with self.subTest("MQTT Client loop_start is called"):
            self.test_instance.mqtt.loop_start.assert_called()

    def test_on_connect(self):
        mock_subscribe = self.test_instance._subscribe = MagicMock()
        self.test_instance._on_connect()

        with self.subTest("Published to will topic"):
            self.test_instance.mqtt.publish.assert_called_with(self.test_instance.will_topic, 'online', retain=True)

        with self.subTest("_subscribe is called"):
            mock_subscribe.assert_called()

    def test_on_disconnect(self):
        self.test_instance._on_disconnect()

    def test_disconnect(self):
        self.test_instance._disconnect()
        with self.subTest("MQTT Client disconnect is called"):
            self.test_instance.mqtt.disconnect.assert_called()

        with self.subTest("MQTT Client loop_stop is called"):
            self.test_instance.mqtt.loop_stop.assert_called()

    @patch('asyncio.get_event_loop')
    def test_start(self, mock_get_event_loop):
        mock_loop = mock_get_event_loop.return_value = MagicMock()

        mock_connect = self.test_instance._connect = MagicMock()

        mock_track_brightness = self.test_instance.track_brightness = MagicMock()
        mock_track_xinput = self.test_instance.track_xinput = MagicMock()
        mock_timeout_touch_changes = self.test_instance.timeout_touch_changes = MagicMock()
        self.test_instance.start()

        with self.subTest("Tracking is enabled"):
            self.assertTrue(self.test_instance.track)

        with self.subTest("Loop is created"):
            mock_get_event_loop.assert_called()

        with self.subTest("_connect is called"):
            mock_connect.assert_called()

        with self.subTest("Task created for track_brightness"):
            mock_loop.create_task.assert_has_calls(mock_track_brightness())

        with self.subTest("track_brightness is called"):
            mock_track_brightness.assert_called()

        with self.subTest("Task created for track_xinput"):
            mock_loop.create_task.assert_has_calls(mock_track_xinput())

        with self.subTest("track_xinput is called"):
            mock_track_xinput.assert_called()

        with self.subTest("Task created for timeout_touch_changes"):
            mock_loop.create_task.assert_has_calls(mock_timeout_touch_changes())

        with self.subTest("timeout_touch_changes is called"):
            mock_timeout_touch_changes.assert_called()

        with self.subTest("Loop is run forever"):
            mock_loop.run_forever.assert_called()

    @patch('asyncio.get_event_loop')
    def test_stop(self, mock_get_event_loop):
        mock_loop = mock_get_event_loop.return_value = MagicMock()

        mock_disconnect = self.test_instance._disconnect = MagicMock()
        mock_unsubscribe = self.test_instance._unsubscribe = MagicMock()

        self.track = True

        self.test_instance.stop()

        with self.subTest("Tracking is disabled"):
            self.assertFalse(self.test_instance.track)

        with self.subTest("Loop is retrieved"):
            mock_get_event_loop.assert_called()

        with self.subTest("_disconnect is called"):
            mock_disconnect.assert_called()

        with self.subTest("_unsubscribe is called"):
            mock_unsubscribe.assert_called()

        with self.subTest("Loop is stopped"):
            mock_loop.stop.assert_called()
