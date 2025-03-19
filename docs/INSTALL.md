# Pixil Installation Guide

This guide will help you set up Pixil to run on your Raspberry Pi with an RGB LED matrix display.

## Hardware Requirements

- **Raspberry Pi**: Model 4 recommended (Model 3B+ also works well)
- **RGB LED Matrix**: 64x64, 64x32 RGB LED matrix panel or other matrix configuration
- **Power Supply**: 5V power supply with sufficient amperage for your matrix
  - For a 64x64 matrix at full brightness, a 4-5A supply is recommended
- **Cables & Connectors**: As required by your specific matrix
- **Adafruit RGB Matrix Bonnet for Raspberry Pi**: Optimal, but makes it a whole lot easier to connect your matrix to your raspberry pi. It has an easy setup process to install the underlying RGBMatrix lib.

## Software Requirements

- Raspberry Pi OS (formerly Raspbian) - Bullseye or newer recommended
- Python 3.7+ 
- Git (for cloning the repository)

## Step 1: Prepare Your Raspberry Pi

Make sure your Raspberry Pi has the latest updates:

```bash
sudo apt update
sudo apt upgrade -y
```

Install required system dependencies:

```bash
sudo apt install -y python3-pip python3-dev python3-pil
sudo apt install -y libatlas-base-dev
sudo apt install -y git
```

## Step 2: Install the RGB Matrix Library

Pixil depends on the rpi-rgb-led-matrix library by Henner Zeller:

```bash
# Clone the library
git clone https://github.com/hzeller/rpi-rgb-led-matrix.git
cd rpi-rgb-led-matrix

# Build and install
make
cd bindings/python
make build
sudo make install
```

## Step 3: Install Pixil

Clone the Pixil repository:

```bash
cd ~
git clone https://github.com/kklasmeier/pixil-led-matrix.git
cd pixil-led-matrix
```

Set up a Python virtual environment (recommended):

```bash
python3 -m venv python_venv
source python_venv/bin/activate
```

Install Python dependencies:

```bash
pip install -r requirements.txt
```

## Step 4: Connect Your Hardware

Pixil supports multiple hardware connection methods for your RGB LED matrix. Choose the option that matches your setup:

### Option A: Adafruit RGB Matrix Bonnet (Recommended)

The Adafruit RGB Matrix Bonnet is an easy, low-cost way to drive RGB LED matrices from a Raspberry Pi.

https://learn.adafruit.com/adafruit-rgb-matrix-bonnet-for-raspberry-pi/

1. **Power off your Raspberry Pi before connecting any hardware**

2. **Install the Adafruit RGB Matrix Bonnet**
   - Attach the bonnet to your Raspberry Pi's GPIO pins. You might need a raiser pin if you have a fan.
   - Connect your matrix to the HUB75 connector on the bonnet
   - Connect power to the bonnet's power terminals (not to the Raspberry Pi's USB)

3. **Install Adafruit's software**
   ```bash
   curl -O https://raw.githubusercontent.com/adafruit/Raspberry-Pi-Installer-Scripts/master/rgb-matrix.sh
   sudo bash rgb-matrix.sh
   ```

4. **During installation:**
   - Select "Configure options manually" when prompted
   - Choose "Adafruit RGB Matrix Bonnet" when asked about your hardware
   - Select quality vs. convenience based on your preference
   - Reboot when prompted

For more detailed instructions, see Adafruit's guide: https://learn.adafruit.com/adafruit-rgb-matrix-bonnet-for-raspberry-pi/

### Option B: Direct GPIO Connection

1. **Power off your Raspberry Pi before connecting the LED matrix**
2. Connect your LED matrix to the Raspberry Pi GPIO pins
   - Follow the pinout diagram for your specific matrix
   - Generally, the matrix will connect to the GPIO pins for data and clock signals

### Configuration

Create a configuration file (if one doesn't exist):

```bash
cp config_example.json config.json
```

Edit the configuration to match your matrix specifications:

```bash
nano config.json
```

Example configuration:

```json
{
  "hardware": {
    "rows": 64,
    "cols": 64,
    "chain_length": 1,
    "parallel": 1,
    "pwm_bits": 11,
    "brightness": 50,
    "hardware_mapping": "regular",
    "gpio_slowdown": 2
  },
  "program": {
    "default_script_path": "scripts/examples",
    "debug_level": 1
  }
}
```

#### Configuration for Adafruit RGB Matrix Bonnet

If you're using the Adafruit RGB Matrix Bonnet, use these settings:

```json
{
  "hardware": {
    "rows": 64,
    "cols": 64,
    "chain_length": 1,
    "parallel": 1,
    "pwm_bits": 11,
    "brightness": 50,
    "hardware_mapping": "adafruit-hat",
    "gpio_slowdown": 2
  },
  "program": {
    "default_script_path": "scripts/examples",
    "debug_level": 1
  }
}
```

Note the `"hardware_mapping": "adafruit-hat"` setting, which is important for the bonnet to work correctly.

Adjust these settings based on your specific matrix. The `gpio_slowdown` parameter may need adjustment depending on your Raspberry Pi model (use higher values like 3 or 4 for Raspberry Pi 4).

## Step 5: Test Your Installation

Run one of the example scripts to verify everything is working:

```bash
python Pixil.py scripts/examples/bouncing_ball.txt
```

If successful, you should see a bouncing ball animation on your LED matrix.

## Troubleshooting

### Permission Issues

If you encounter permission errors when accessing the GPIO, run Pixil with sudo:

```bash
sudo python Pixil.py scripts/examples/bouncing_ball.txt
```

For a more permanent solution, add your user to the gpio group:

```bash
sudo usermod -a -G gpio $USER
sudo usermod -a -G spi $USER
```

#### Adafruit RGB Matrix Bonnet Permissions

If you're using the Adafruit RGB Matrix Bonnet, the installer should have already set up the necessary permissions. If you still encounter permission issues:

```bash
# Make sure you have access to the device
sudo chmod a+rw /dev/spidev0.0
sudo chmod a+rw /dev/spidev0.1
```

### Display Problems

If the display looks distorted or flickering:

1. Try adjusting the `gpio_slowdown` parameter in your config
2. Check all physical connections
3. Ensure adequate power is supplied to both Raspberry Pi and LED matrix

### Command Queue Backlog

If animations become sluggish due to command queue backlog:

1. Use the `throttle` command in your scripts
2. Reduce animation complexity
3. Add occasional `sync_queue` commands

## Starting Pixil on Boot

To have Pixil start automatically when your Raspberry Pi boots:

1. Create a systemd service file:

```bash
sudo nano /etc/systemd/system/pixil.service
```

2. Add the following content (adjust paths as needed):

```
[Unit]
Description=Pixil LED Matrix Service
After=network.target

[Service]
User=pi
WorkingDirectory=/home/pi/pixil-led-matrix
ExecStart=/home/pi/pixil-led-matrix/python_venv/bin/python Pixil.py scripts/examples/starfield.txt
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

3. Enable and start the service:

```bash
sudo systemctl enable pixil.service
sudo systemctl start pixil.service
```

## Next Steps

- Explore the example scripts in the `scripts/examples/` directory
- Create your own scripts in the `scripts/user/` directory
- Read the full language reference in the README.md file

For more information, check out the project documentation and examples.
