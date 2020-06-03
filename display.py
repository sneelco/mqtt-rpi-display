#!/usr/bin/env python3

import logging
import argparse
from mqttRPiDisplay import RPiDisplay

parser = argparse.ArgumentParser(description='Manage RPi Display through MQTT')
parser.add_argument('-n', '--name', dest="name", help='The name of this device')
parser.add_argument('-H', '--host', dest='host', help='MQTT HOst')

args = parser.parse_args()

logging.basicConfig(level=logging.INFO)
display = RPiDisplay(args.name, args.host)
display.start()
