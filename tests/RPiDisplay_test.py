from unittest import TestCase
from unittest.mock import patch, mock_open, MagicMock

from mqttRPiDisplay import RPiDisplay

TEST_NAME = "test-display"
TEST_HOST = "localtest"
TEST_READ_BRIGHTNESS = "100\n"


class RPiDisplayTest(TestCase):

    @patch('builtins.open', mock_open(read_data=TEST_READ_BRIGHTNESS))
    @patch('paho.mqtt.client.Client')
    def setUp(self, mock_mqtt):
        mock_client = mock_mqtt.side_effect = MagicMock()
        self.test_instance = RPiDisplay(TEST_NAME, TEST_HOST)
        self.mock_client = mock_client

    def test_init(self):
        self.assertTrue(self.mock_client.called)

    @patch('builtins.open', mock_open(read_data=TEST_READ_BRIGHTNESS))
    def test_get_brightness(self):
        self.assertEqual(self.test_instance.get_brightness(), int(TEST_READ_BRIGHTNESS))

    def test_set_brightness(self):
        with patch('builtins.open', mock_open()) as mock_file:
            self.test_instance.set_brightness(50)
            mock_file().write.assert_called_once_with("50")

    def test_publish_brightness(self):
        self.test_instance.publish_brightness(200)

        with self.subTest('Published is called'):
            self.test_instance.mqtt.publish.assert_called()

        with self.subTest('Published called with test brightness'):
            self.test_instance.mqtt.publish.assert_called_once_with(None, 200, retain=True)

        with self.subTest('Instance brightness is set'):
            self.assertEqual(self.test_instance.brightness, 200)

    def test_subscribe_brightness(self):
        self.assertTrue(False)

    def test_track_brightness(self):
        self.assertTrue(False)

    def test_start(self):
        self.assertTrue(False)

    def test_stop(self):
        self.assertTrue(False)

