# Pixil Installation Guide

This guide will help you set up Pixil to run on your Raspberry Pi with an RGB LED matrix display.

## Hardware Requirements

- **Raspberry Pi**: Model 4 recommended (Model 3B+ also works well)
- **RGB LED Matrix**: 64x64 RGB LED matrix panel (other sizes like 64x32 will work but may require configuration adjustments)
- **Power Supply**: 5V power supply with sufficient amperage for your matrix
  - For a 64x64 matrix at full brightness, a 5A supply is recommended
- **Adafruit RGB Matrix Bonnet** (Recommended): Makes connecting your matrix to the Raspberry Pi simple and reliable
- **Optional**: IDC cable if your matrix isn't directly attachable to the bonnet

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

## Step 2: Hardware Setup with Adafruit RGB Matrix Bonnet (Recommended)

The Adafruit RGB Matrix Bonnet provides the most reliable connection method for driving RGB LED matrices.

1. **Power off your Raspberry Pi before connecting any hardware**

2. **Install the Adafruit RGB Matrix Bonnet**
   - Attach the bonnet to your Raspberry Pi's GPIO pins (you may need a header extender if you have a cooling fan)
   - Connect your matrix to the HUB75 connector on the bonnet
   - Connect the 5V power supply to the bonnet's power terminals (NOT to the Raspberry Pi's USB port)

3. **Install Adafruit's RGB Matrix software**
   ```bash
   curl -O https://raw.githubusercontent.com/adafruit/Raspberry-Pi-Installer-Scripts/master/rgb-matrix.sh
   sudo bash rgb-matrix.sh
   ```

4. **During installation:**
   - Select "Configure options manually" when prompted
   - Choose "Adafruit RGB Matrix Bonnet" when asked about your hardware
   - Select quality vs. convenience based on your preference (quality recommended for best visual results)
   - Reboot when prompted

For detailed wiring instructions, see [Adafruit's official guide](https://learn.adafruit.com/adafruit-rgb-matrix-bonnet-for-raspberry-pi/).

## Step 3: Install the RGB Matrix Library

Pixil depends on the rpi-rgb-led-matrix library by Henner Zeller. The Adafruit installer from Step 2 should have installed this already, but if you need to install it manually:

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

## Step 4: Install Pixil

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

## Step 5: Configure Pixil

Create a configuration file (if one doesn't exist):

```bash
cp config_example.json config.json
```

Edit the configuration to match your matrix specifications:

```bash
nano config.json
```

### For Adafruit RGB Matrix Bonnet (Recommended)

Use these settings if you're using the Adafruit RGB Matrix Bonnet:

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
    "gpio_slowdown": 3
  },
  "program": {
    "default_script_path": "scripts/examples",
    "debug_level": 1
  }
}
```

Important settings:
- `"hardware_mapping": "adafruit-hat"` - Critical for the bonnet to work correctly
- `"gpio_slowdown": 3` - Recommended for Raspberry Pi 4 (use 2 for Pi 3, 1 for older models)
- `"brightness": 50` - Adjust between 0-100 based on your power supply capacity

## Step 6: Test Your Installation

Run one of the example scripts to verify everything is working:

```bash
sudo python Pixil.py main/Color_Blend
```

Note: The `.pix` extension is optional when running scripts.

If successful, you should see a bouncing ball animation on your LED matrix.

## Troubleshooting

### Permission Issues

For the best experience, run Pixil with sudo:

```bash
sudo python Pixil.py main/Color_Blend
```

For a more permanent solution, add your user to the required groups:

```bash
sudo usermod -a -G gpio,spi $USER
# Log out and back in for changes to take effect
```

### Display Problems

If the display looks distorted or flickering:

1. Check your power supply - insufficient power is the most common cause of display issues
2. Try adjusting the `gpio_slowdown` parameter in your config (increase for Pi 4, decrease for older models)
3. Verify all physical connections between the bonnet and matrix
4. Lower the brightness setting in the config file

### Command Queue Backlog

If animations become sluggish:

1. Use the `throttle` command in your scripts to adjust animation speed
2. Add occasional `sync_queue` commands to prevent queue overruns
3. Reduce animation complexity in high-activity scenes

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
User=root
WorkingDirectory=/home/pi/pixil-led-matrix
ExecStart=/home/pi/pixil-led-matrix/python_venv/bin/python Pixil.py scripts/examples/starfield
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Note: Using `User=root` avoids permission issues with GPIO access.

3. Enable and start the service:

```bash
sudo systemctl enable pixil.service
sudo systemctl start pixil.service
```

## Next Steps

- Explore the example scripts in the `scripts/examples/` directory
- Create your own scripts using the Pixil scripting language
- Read the full language reference in the README.md file

For more information, check out the [project documentation](https://github.com/kklasmeier/pixil-led-matrix) and examples.

## Support

If you encounter issues not covered in this guide, please file an issue on the GitHub repository.