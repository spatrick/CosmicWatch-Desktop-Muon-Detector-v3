This folder contains:

1. The import_data.py code. 
This file can be run using python to communicate with your detector. The purpose of using this, rather than say the microSD card, is that the timestamp of each event would come from the computer rather than the Teensy, and is therefore more likely to be more accurate. You can also use this code to record multiple detectors to a single file. If you connect multiple detectors to your computer via a USB hub (or multiple USB ports), you can select multiple detectors to record data from using a ',' between names when prompted. This code requires several libraries, including Pyserial and Tornado -- these are available through pip.  
