import sys
import json
import signal
import logging

import paho.mqtt.client as mqtt

from time import sleep

session_id = ""

def session_topic():
    return 'dfsm:{}'.format(session_id)

def session_topic_response():
    return '{}:response'.format(session_topic())


def load_json(fname):
    opened_file = open(fname)
    result = json.load(opened_file)
    opened_file.close()
    return result

def load_config():
    try:
        console_config = load_json('config.json')
    except FileNotFoundError:
        logging.error('Cannot load a config file!')
        sys.exit(1)
        
    logging.info('Loaded config: Host - {}, port - {}'.format(
        console_config['hostname'], console_config['port']))

    return console_config

class Listening_State:

    def _stop_listening_signal(self, signum, frame):
        self.listening = False
        logging.info('Stopped listening to {} of device {}'.format(
            self.device['topic'], self.device['name']))
        self.console.state = Main_State(self.console)
        self.console.client.unsubscribe(self.device['topic'])
    
    def __init__(self, console, device):
        self.console = console
        self.device = device
        self.listening = True
        signal.signal(signal.SIGINT, self._stop_listening_signal)
        self.console.client.subscribe(device['topic'])

    def update(self):
        pass
    
    def on_message(self, msg):
        if self.listening:
            logging.info(msg)

class Main_State:
    def __init__(self, console):
        self.console = console

    def _print_help(self):
        delim = ' - '
        commands = {
            'help' : 'prints existing commands',
            'q': 'stops the console',
            'stop_session' : 'stops named session',
            'stop_device' : 'stops device with given id',
            'gather' : 'gather existing devices',
            'list': 'list gathered devices',
            'listen_device': 'listens to the device with given id',
            'stat_all': 'Print stats of all previously gathered devices',
            'stat': 'Print stats of a device with given id'
        }

        for k,v in commands.items():
            print('{}{} - {}'.format(delim, k, v))

    def _stop_console(self):
        self.console.running = False
            
    def _stop_session(self):
        msg = {
            'cmd': 'stop_session',
        }

        self.console.client.publish(session_topic(), json.dumps(msg), 0)

    def _stop_device(self):
        device_id = int(input('Enter device id >>> '))

        msg = {
            'cmd': 'stop_device',
            'id': device_id
        }

        self.console.client.publish(session_topic(), json.dumps(msg), 0)

    def _gather_devices(self):
        msg = {
            'cmd': 'gather'
        }

        self.console.client.publish(session_topic(), json.dumps(msg), 0)

    def _list_devices(self):
        if len(self.console.devices) > 0:
            logging.info('{} devices are connected to the console: '.format(
                len(self.console.devices)))
            for k, v in self.console.devices.items():
                logging.info('- {} (with id {})'.format(v['name'], v['id']))

    def _listen_to_device(self):
        device_id = int(input('Enter device id >>> '))
        device = self.console.devices.get(device_id)
        if device:
            self.console.state = Listening_State(self.console, device)

    def _print_device_stats(self, device):
        logging.info('stats of {} (with id {}):'.format(device['name'], device['id']))
        logging.info(' - sent packets {}'.format(device['stats']['sent_packets']))
        logging.info(' - sent size {}'.format(device['stats']['sent_size']))
        logging.info(' - dropped packets {}'.format(device['stats']['dropped_packets']))
        logging.info(' - dropped size {}'.format(device['stats']['dropped_size']))        


    def _stat_all_devices(self):
        for device in self.console.devices.values():
            self._print_device_stats(device)
            logging.info('')

    def _stat_device(self):
        device_id = int(input('Enter device id >>> '))
        device = self.console.devices.get(device_id)
        if device:
            self._print_device_stats(device)
        else:
            logging.error('Device with given name is not found! (possibly you forgot to use "gather" before')

            
    def update(self):
        user_input = input('Enter command ("help" to get help) >>> ')
        processors = {
            'h': self._print_help,
            'help': self._print_help,
            'q': self._stop_console,
            'quit': self._stop_console,
            'stop_session': self._stop_session,
            'stop_device': self._stop_device,
            'gather': self._gather_devices,
            'list': self._list_devices,
            'listen': self._listen_to_device,
            'stat_all': self._stat_all_devices,
            'stat': self._stat_device
        }

        processor = processors.get(user_input)
        processor() if processor else None
        
    def on_message(self, msg):
        print(msg)
        if msg['cmd'] == 'gather':
            logging.info('gathered: {}'.format(msg['data']['name']))
            self.console.devices[msg['data']['id']] = msg['data']
            self.console.devices[msg['data']['id']]['stats'] = msg['stats']
        elif msg['cmd'] == 'stop_device':
            logging.info(msg['msg'])
        
class Console:
    def __init__(self, config):
        self.config = config
        self.state = Main_State(self)
        self.devices = {}

    def _on_connect(self, client, userdata, flags, rc):
        logging.info('Connected successfully!')
        client.subscribe(session_topic_response())
        self.connected = True

    def _on_disconnect(self, client, userdata, rc):
        logging.info('Disconnected successfully!')
        
    def _on_message(self, client, userdata, inmsg):
        msg = json.loads(inmsg.payload)
        logging.info(msg)

        self.state.on_message(msg)
        
    def _setup_connection(self):
        config = self.config
        
        self.client = mqtt.Client()
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        self.client.connect(config['hostname'], config['port'], config.get('keepalive', 20))
        self.client.loop_start()
        
    def run(self):
        self.connected = False
        self.running = True        
        self._setup_connection()

        while not self.connected:
            sleep(0.1)
        
        while self.running:
            self.state.update()

def main(argv):
    logging.basicConfig(format='[console][%(asctime)s] %(message)s', level=logging.DEBUG)
    
    if len(argv) != 2:
        logging.error('Usage: {} session-id'.format(argv[0]))
        return
    else:
        global session_id
        session_id = argv[1]
    
    config = load_config()
    console = Console(config)
    console.run()

if __name__ == '__main__':
    main(sys.argv)
