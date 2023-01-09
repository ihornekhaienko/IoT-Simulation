# data flow simulator core

import sys
import logging
import json
import signal
import uuid
from threading import Thread

import dfsm_settings as settings
from dfsm_device import *

registered_devices = {}

class DiscreteSampler:
    def __init__(self, data):
        points_sum = sum(data['points'])
        self.rng = data['range']
        self.points = [x / points_sum for x in data['points']]
        self.acc_points = [x for x in self.points]
        self.acc_points[0] = self.points[0]
        for i in range(1, len(self.acc_points)):
            self.acc_points[i] = self.acc_points[i - 1] + self.points[i]

    def inv_cdf(self, params):
        e = params['e']
        bucket_idx = 0
        prev_value = 0
        for i, value in enumerate(self.acc_points):
            if e >= prev_value and e < value:
                bucket_idx = i
                break
            prev_value = value

        bucket_size = 1.0 / len(self.points)

        if bucket_idx == 0:
            # extrapolate to 0
            x = (e / self.acc_points[0]) * bucket_size
        else:
            # interpolate between bucket's edge acc points
            e1 = self.acc_points[bucket_idx - 1]
            e2 = self.acc_points[bucket_idx]
            s = (e - e1) / (e2 - e1) * bucket_size
            x = bucket_idx * bucket_size + s

        rng = self.rng
        return x * (rng[1] - rng[0]) + rng[0]
            
def parse_input(argv):
    return {}

def load_json(fname):
    opened_file = open(fname)
    result = json.load(opened_file)
    opened_file.close()
    return result

def load_config():
    try:
        core_config = load_json('config.json')
    except FileNotFoundError:
        logging.error('Cannot load a config file!')
        sys.exit(1)
        
    logging.info('Loaded config: Host - {}, port - {}'.format(
        core_config['hostname'], core_config['port']))

    return core_config
    
def load_devices():
    try:
        devices = load_json('devices.json')
    except FileNotFoundError:
        logging.error('No devices were provided!')
        sys.exit(2)

    logging.info('{} device(s) {} loaded!'.format(
        len(devices), 'were' if len(devices) > 1 else 'was'))

    return devices

def load_distributions():
    try:
        distributions = load_json('distributions.json')
    except FileNotFoundError:
        logging.error('No distributions were provided!')
        sys.exit(3)

    for dname, ddata in distributions.items():
        settings.distributions[dname] = {}
        settings.distributions[dname]['type'] = ddata.get('type')
        settings.distributions[dname]['range'] = ddata['range']
        
        if settings.distributions[dname]['type'] == 'continious':
            settings.distributions[dname]['func'] = __import__(ddata['inv_cdf_file'], fromlist=(dname)).inv_cdf
        elif settings.distributions[dname]['type'] == 'discrete':
            sampler = DiscreteSampler(ddata)
            settings.distributions[dname]['func'] = sampler.inv_cdf
        else:
            logging.error('"{}" distribution function has unknown type, allowed are: continious/discrete'.format(
                dname))

def generate_session_id():
    settings.session_id = str(uuid.uuid1())
    logging.info('Use next session-id to communicate with devices: {}'.format(
        settings.session_id))
            
def signal_handler(signum, frame):
    settings.signaled_to_stop = True
    logging.info('Stopping the simulator...')

def main_loop(parsed_input, config, devices):

    global registered_devices

    threads = []
    for device_data in devices.values():
        device = Device(config, device_data)
        registered_devices[device_data['id']] = device
        thread = Thread(target = device_main, args=(device,))
        thread.start()
        threads.append(thread)

    signal.signal(signal.SIGINT, signal_handler)

    while not settings.signaled_to_stop:
        pass
    
    for thread in threads:
        thread.join()

    
def main(argv):
    parsed_input = parse_input(argv)
    logging.basicConfig(format='[%(asctime)s] %(message)s', level=logging.DEBUG)

    config = load_config()
    devices = load_devices()
    load_distributions()
    generate_session_id()

    main_loop(parsed_input, config, devices)
    
if __name__ == '__main__':
    main(sys.argv)
