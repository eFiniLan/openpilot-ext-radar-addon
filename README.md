# openpilot External Radar Addon

## Overview
This project enables sensor fusion in openpilot by integrating an external radar. The radar is mounted on the windshield and connected to the vehicle's OBD2 port for both power and signal transmission. With openpilot also connected to the OBD2 port, it can read radar data, enhancing its perception capabilities.

## Why This Project?
Some vehicles with openpilot installed can only use Vision-Only Adaptive Cruise Control (VOACC). By adding an external radar to the car, sensor fusion enables more accurate lead car speed detection and distance measurement, significantly improving safety and performance.

**The guide and code are designed for Toyota vehicles**. If using a different vehicle, you will need:
   - Modify the code to use the correct CAN channel.
   - Adjust the distance from the vehicle front to the radar if mounting in front of the vehicle.
   - Ensure CAN message compatibility to avoid conflicts with the vehicle's existing communication.

## Prerequisites
Before installing this addon, ensure you have the following:
- A car that already has openpilot installed.
- The car must support openpilot longitudinal control.
- The car does not have radar support. (e.g. Nissan, Volkswagen, Mazda, Subaru...)
- A comma 3 or 3X device.
- A comma 3 or 3X running **openpilot version 0.9.8 or above**.

## Bill of Materials (BOM)
1. [Radar](https://www.aliexpress.com/item/1005006713716767.html), ~$236 USD
2. GoPro Accessories:
   * [Cell Phone Holder](https://www.aliexpress.com/item/1005007539814670.html), ~$4.0 USD
   * [1/4 inch Mount](https://www.aliexpress.com/item/1005006410768280.html), ~$1.0 USD
   * [Short Screw](https://www.aliexpress.com/item/32819832442.html), ~$1.2 USD
   * [Quick Release Buckle Mount](https://www.aliexpress.com/item/1005006410768280.html), ~$1.0 USD
   * [Short Screw](https://www.aliexpress.com/item/32819832442.html), ~$1.2 USD
   * [Flat Adhesive Mount](https://www.aliexpress.com/item/1005006441304068.html), ~$0.99 USD
3. [4 Pins Phoenix Type Connector](https://www.aliexpress.com/item/1005006554550534.html), ~$2.00 USD

## Installation

## Hardware Build
### Wiring
![0ad176a15aa93dfece0d144b085280f1](https://github.com/user-attachments/assets/7cacb8bf-00bc-431b-bf26-78cb610537fd)
### Radar Mount
![91f0ffd1e2a280c6983ec02e0e43d259](https://github.com/user-attachments/assets/1ea0f87f-c736-4587-bbfe-b7a86333b1ed)
### Mounting Example
![cf6ec2886d137ccc931ce7a3d0f34eae](https://github.com/user-attachments/assets/f98151be-1a3e-49cb-8697-aa39b19c6ec2)

### Hardware Setup
1. **Mount the Radar**: Secure the radar unit onto the windshield.
2. **Connect to OBD2 Port**: Use the provided adapter to link the radar’s signal and power to the OBD2 port.

### Wiring Diagram
Connect the radar and openpilot to the OBD2 cable as follows:

| OBD2 Cable Pin | Radar Cable | openpilot Cable |
|---------------|------------|----------------|
| Pin 14        | CAN L (green) | CAN L (green) |
| Pin 6         | CAN H (yellow) | CAN H (yellow) |
| Pin 5         | Ground (black) | Ground (black) |
| Pin 16        | 12V (red) | 12V (red) |

### Software Setup (tested on 0.9.8)

#### opendbc/dbc/u_radar.dbc
Upload to /data/openpilot/opendbc/dbc/u_radar.dbc

#### opendbc/dbc/u_radar_config.py
1. Upload to /data/openpilot/opendbc/dbc/u_radar_config.py
2. Change radar settings:
```
# manually terminate openpilot
tmux a
press "<ctrl> + c" several times

# apply settings
cd /data/openpilot/opendbc/dbc/ && python u_radar_config.py 
```

#### opendbc/car/radar_interface.py
Upload to /data/openpilot/opendbc/car/radar_interface.py

#### Apply card.py change
1. upload panda.diff to /data
2. Apply changes:
```bash
cd /data/openpilot/ && git apply ../card.diff
```


## Notes
**Mounting Bracket**: The provided mounting bracket is designed as a temporary solution to allow easy adjustment and removal of the radar unit.

## Contributing
Contributions are welcome! Please submit issues or pull requests to improve functionality.

## License
This project is licensed under MIT Non-Commercial License.

See the [LICENSE](LICENSE.md) file for complete details.

## Acknowledgments
Thanks to the openpilot community for ongoing support and development.
