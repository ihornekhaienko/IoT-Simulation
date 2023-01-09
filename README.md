# IoT-Simulation
The project consists of two main parts: the Simulator and the Console.

## Simulator
The user is able to describe the data to be simulated using the json file. In fact, in this file it describes all the devices that need to be simulated, for each device it specifies:
- Id
- Title
- Topic
- And various parameters regarding the data (distribution type, value limits, number of channels (for example, if we generate a color, then there will be 3 channels - for RGB), the chance of an unsuccessful packet)

There are two types of distributions:
1. Continuous - There are three such distributions in the standard set: linear, constant, exponential. The user can program them on their own (you need to create a script in the distributions folder in the python language, and also describe this new type in the distributions.json file)
2. Discrete - In the standard set there is only a normal distribution. The user can also create his own distributions: in fact, he simply sets a set of points, and the program already creates a sampler based on them.

Each device is launched by the simulator in a separate thread.

When the simulator is launched, it generates a random UUID - this is the key by which it will be possible to connect to the simulator from the console (or from another application) and communicate with the simulator (for example, turn virtual devices on and off, collect statistics on them, listen, etc.)

## Console
The console is an independent program. When starting the console, we specify the UUID and the console connects to the broker and communicates with the simulator through it. The following commands are supported:
1. q - stop the console
2. stop_device - stop the device with the specified id
3. stop_session - stop the simulator
4. gather - collect information on all devices that are on the simulator
5. list - displays a list of devices (you need to use gather before that)
6. listen_device - switches to listening mode for the specified device
7. stat_all - displays statistics for all devices (you must first use gather)
8. stat - displays statistics on the specified device (number of packets sent, number of bytes sent, etc.)

There are other options to add modify, which would allow, for example, editing devices in real time.
