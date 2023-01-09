import sys
import json
import logging
import paho.mqtt.client as mqtt

import dfsm_settings as settings

from time import sleep
from random import random
from datetime import datetime

class Device:

    def __init__(self, config, device_data):
        self.config = config
        self.device_data = device_data
        self.device_data['stopped'] = False
        self.stats = {
            'sent_packets': 0,
            'sent_size': 0,
            'dropped_packets': 0,
            'dropped_size': 0
        }

    def device_full_name(self):
        return '{} (id {})'.format(self.device_data['name'], self.device_data['id'])

    def session_topic(self):
        return 'dfsm:{}'.format(settings.session_id)

    def session_topic_response(self):
        return '{}:response'.format(self.session_topic())

    def _should_be_dropped(self):
        return random() < self.device_data['drop_rate']
    
    def _on_connect(self, client, userdata, flags, rc):
        logging.info('{} has connected!'.format(self.device_full_name()))
        client.subscribe(self.session_topic())
        
    def _on_connect_fail(self, client, userdata, flags, rc):
        logging.info('fail')

    def _on_disconnect(self, client, userdata, rc):
        logging.info('{} has disconnected!'.format(self.device_full_name()))
        
    def _on_message(self, client, userdata, inmsg):
        message = json.loads(inmsg.payload)
        processors = {
            'stop_session': Device._process_stop_session,
            'stop_device': Device._process_stop_device,
            'gather': Device._process_gather,
        }

        processor = processors.get(message.get('cmd'))
        processor(self, message) if processor else None

    def _process_stop_session(self, message):
        assert message['cmd'] == 'stop_session'
        settings.signaled_to_stop = True

    def _process_stop_device(self, message):
        assert message['cmd'] == 'stop_device'
        if message['id'] == self.device_data['id']:
            self.device_data['stopped'] = True
            logging.info('Stopping {}'.format(self.device_full_name()))
            response = {
                'cmd': 'stop_device',
                'id': self.device_data['id'],
                'msg': 'Device {} has stopped!'.format(self.device_full_name())
            }
            self.client.publish(self.session_topic_response(), json.dumps(response))
            

    def _process_gather(self, message):
        assert message['cmd'] == 'gather'
        response = {
            'cmd': 'gather',
            'data': self.device_data,
            'stats': self.stats
        }
        self.client.publish(self.session_topic_response(), json.dumps(response))
        
    def _generate_data(self):
        distribution_data = self.device_data['distribution']
        params = distribution_data['data']
        params['e'] = random()

        distribution = settings.distributions[distribution_data['type']]
        value = distribution['func'](params)
        value -= distribution['range'][0]
        value /= (distribution['range'][1] - distribution['range'][0])
        value *= distribution_data['range'][1] - distribution_data['range'][0]
        value += distribution_data['range'][0]
        
        return {
            'type': self.device_data['data_type'],
            'grade': self.device_data['data_grade'],
            'value': value,
            'timestamp': datetime.timestamp(datetime.now())
        }


    def _setup_connection(self):
        config = self.config
        
        self.client = mqtt.Client()
        self.client.on_connect = self._on_connect
        self.client.on_connect_fail = self._on_connect_fail
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        self.client.connect(config['hostname'], config['port'], config.get('keepalive', 20))
    
    def run(self):
        config = self.config
        device_data = self.device_data
        
        self._setup_connection()
        
        while not settings.signaled_to_stop and not device_data['stopped']:
            self.client.loop()

            if not self._should_be_dropped():
                data = []
                for i in range(0, device_data['data_channels']):
                    data.append(self._generate_data())


                self.client.publish(device_data['topic'], json.dumps(data), device_data.get('qos', 0))
                self.stats['sent_packets'] += 1
                self.stats['sent_size'] += sys.getsizeof(data)
            else:
                self.stats['dropped_packets'] += 1
                self.stats['dropped_size'] += sys.getsizeof(data)
                
            sleep(1 / device_data['frequency'])

        self.client.disconnect()
            
def device_main(device):
    device.run()
