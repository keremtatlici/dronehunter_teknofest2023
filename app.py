#!/usr/bin/env python3

from pathlib import Path
from types import SimpleNamespace
import argparse
import logging
import json
import cv2

import fastmot
import fastmot.models
from fastmot.utils import ConfigDecoder, Profiler
from dronekit import connect,Vehicle
from time import sleep
from dronekit import LocationGlobalRelative
import datetime
import math


#python3 app.py --mot --show --input-uri testset/siha1-input.mp4 --output-uri outputs/siha1-output1.mp4
#“[Kategorisi]_[Müsabaka No]_[Takım adı]_[Tarih(gg/aa/yyyy)]”
#“SabitKanat_4_Atmosfer-Havacilik-Takimi_07_09_2021.mp4”
#python3 app.py --mot --show --input-uri /dev/video2 --output-uri outputs/SabitKanat_7_Atmosfer-Havacilik-Takimi_09_09_2021.mp4 -p -a
#mavproxy.py --console --master=/dev/serial/by-id/usb-FTDI_FT232R_USB_UART_AR0K76MI-if00-port0 --baudrate 57600 --out 127.0.0.1:14550
class MyVehicle(Vehicle):
    """
    Custom Vehicle class inheriting from DroneKit's Vehicle.
    Used to access system time messages and store them in a custom structure.
    """
    def __init__(self, connection_string):
        super(MyVehicle, self).__init__(connection_string)
        self._system_time = SystemTIME()

        # Register a listener for MAVLink SYSTEM_TIME messages to keep track
        # of Unix time and boot time in milliseconds.
        @self.on_message('SYSTEM_TIME')
        def listener(self, name, message):
            self._system_time.time_boot_unix=int (message.time_unix_usec)
            self._system_time.time_boot_ms = int (message.time_boot_ms )


    @property
    def system_time(self):
        """
        Exposes the system_time object so it can be accessed like vehicle.system_time.
        """
        return self._system_time

class SystemTIME(object):
    """
    Simple class to store system time data from the drone.
    """
    def __init__(self, time_boot_unix=None , time_boot_ms=None):
        self.time_boot_unix = time_boot_unix
        self.time_boot_ms = time_boot_ms
    def __str__(self):
        # Return the Unix time as a string
        return "{}".format(self.time_boot_unix,self.time_boot_ms)


# ------------------- ARGUMENT PARSING ------------------- #
parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)

# Separate optional vs. required arguments for readability
optional = parser._action_groups.pop()
required = parser.add_argument_group('required arguments')

# Mutually exclusive group for verbosity control (quiet or verbose)
group = parser.add_mutually_exclusive_group()

# Required argument: input URI
required.add_argument('-i', '--input-uri', metavar="URI", required=True, help=
                        'URI to input stream\n'
                        '1) image sequence (e.g. %%06d.jpg)\n'
                        '2) video file (e.g. file.mp4)\n'
                        '3) MIPI CSI camera (e.g. csi://0)\n'
                        '4) USB camera (e.g. /dev/video0)\n'
                        '5) RTSP stream (e.g. rtsp://<user>:<password>@<ip>:<port>/<path>)\n'
                        '6) HTTP stream (e.g. http://<user>:<password>@<ip>:<port>/<path>)\n')

# Optional arguments
optional.add_argument('-c', '--config', metavar="FILE",
                        default=Path(__file__).parent / 'cfg' / 'mot.json',
                        help='path to JSON configuration file')
optional.add_argument('-l', '--labels', metavar="FILE",
                        help='path to label names (e.g. coco.names)')
optional.add_argument('-o', '--output-uri', metavar="URI",
                        help='URI to output video file')
optional.add_argument('-t', '--txt', metavar="FILE",
                        help='path to output MOT Challenge format results (e.g. MOT20-01.txt)')
optional.add_argument('-m', '--mot', action='store_true', help='run multiple object tracker')

# Custom arguments for hardware connections
#PİXHAWK ARGUMANI EKLENDİ:
optional.add_argument('-p', '--pixhawk', action='store_true', help='pixhawk baglanicaksa satıra yazılması yeterli')
#SUNUCU ARGUMANI EKLENDİ
optional.add_argument('-a', '--sunucu', action='store_true', help='sunucuya bağlanacaksan satıra yaz')
#ARDUINO ARGUMANI EKLENDİ
optional.add_argument('-d', '--arduino', action='store_true', help='arduino bağlanacaksan satıra yaz')

# Display arguments
optional.add_argument('-s', '--show', action='store_true', help='show visualizations')

# Verbosity control (mutually exclusive with quiet)
group.add_argument('-q', '--quiet', action='store_true', help='reduce output verbosity')
group.add_argument('-v', '--verbose', action='store_true', help='increase output verbosity')
parser._action_groups.append(optional)
args = parser.parse_args()

# Validate that --txt is only used if --mot is specified
if args.txt is not None and not args.mot:
    raise parser.error('argument -t/--txt: not allowed without argument -m/--mot')


# ------------------- VEHICLE CONNECTION ------------------- #
vehicle = None
if args.pixhawk:
    # Example connection string for a Pixhawk
    # Adjust the serial ID or baud rate as needed for your hardware
    vehicle = connect(
        '/dev/serial/by-id/usb-Hex_ProfiCNC_CubeOrange-bdshot_390020000F51313132383631-if00',
        wait_ready=False,
        baud=57600,
        vehicle_class=MyVehicle
    )

# -------------- EXAMPLE DRONEKIT LOOP (commented out) --------------#
"""
while True:
    telemetry_packet = { 
    "IHA_enlem": vehicle.location.global_relative_frame.lat, 
    "IHA_boylam": vehicle.location.global_relative_frame.lon, 
    "IHA_irtifa": vehicle.location.global_relative_frame.alt, 
    "IHA_dikilme": math.degrees(vehicle.attitude.pitch), 
    "IHA_yonelme": vehicle.heading, 
    "IHA_yatis": math.degrees(vehicle.attitude.roll), 
    "IHA_hiz": vehicle.groundspeed, 
    "IHA_batarya": vehicle.battery.level,  
    "GPSSaati": { 
        "saat": datetime.datetime.fromtimestamp(vehicle.system_time.time_boot_unix/1000000).hour-3, 
        "dakika": datetime.datetime.fromtimestamp(vehicle.system_time.time_boot_unix/1000000).minute, 
        "saniye": datetime.datetime.fromtimestamp(vehicle.system_time.time_boot_unix/1000000).second, 
        "milisaniye": int(datetime.datetime.fromtimestamp(vehicle.system_time.time_boot_unix/1000000).microsecond/1000)}
    }
    print(telemetry_packet)
    sleep(2)
"""
#DATETİME İÇİN FONT
font = cv2.FONT_HERSHEY_SIMPLEX

# ------------------- LOGGING SETUP ------------------- #
logging.basicConfig(format='%(asctime)s [%(levelname)8s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(fastmot.__name__)
if args.quiet:
    logger.setLevel(logging.WARNING)
elif args.verbose:
    logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.INFO)


# ------------------- LOAD CONFIG / LABELS ------------------- #
with open(args.config) as cfg_file:
    config = json.load(cfg_file, cls=ConfigDecoder, object_hook=lambda d: SimpleNamespace(**d))

# load labels if given
if args.labels is not None:
    with open(args.labels) as label_file:
        label_map = label_file.read().splitlines()
        fastmot.models.set_label_map(label_map)

# ------------------- VIDEO STREAM SETUP ------------------- #
stream = fastmot.VideoIO(
    config.resize_to,
    args.input_uri,
    args.output_uri,
    **vars(config.stream_cfg)
)

# Initialize MOT if requested
mot = None
txt = None
if args.mot:
    # If we draw bounding boxes, enable only when showing or if there's an output
    draw = args.show or args.output_uri is not None
    mot = fastmot.MOT(config.resize_to, **vars(config.mot_cfg), draw=draw)
     # Reset or initialize the tracker (important for correct frame timing)
    mot.reset(stream.cap_dt)

# If MOT Challenge format logging is requested, open file for writing
if args.txt is not None:
    Path(args.txt).parent.mkdir(parents=True, exist_ok=True)
    txt = open(args.txt, 'w')

# If user wants to see the frames, create a named OpenCV window
if args.show:
    cv2.namedWindow('Video', cv2.WINDOW_AUTOSIZE)

logger.info('Starting video capture...')
stream.start_capture()
try:
    # Profiler measures performance, e.g. total execution time, average FPS, etc.
    with Profiler('app') as prof:
        while not args.show or cv2.getWindowProperty('Video', 0) >= 0:
            frame = stream.read()
            # If no more frames, break out of loop
            if frame is None:
                break

            if args.mot:
                # Perform a single step of the tracker
                center_x, center_y, bbox_width, bbox_height, target_accuracy =mot.step(frame)
                #print(f"center_x: {center_x}, center_y: {center_y}, bbox_width: {bbox_width}, bbox_height: {bbox_height}, accuracy: {target_accuracy}  ")
                #print(f"accuracy: {target_accuracy}  ")

                # If we have a .txt file open, log results in MOT Challenge format
                if txt is not None:
                    for track in mot.visible_tracks():
                        # Convert bounding boxes from resized scale to the original resolution
                        tl = track.tlbr[:2] / config.resize_to * stream.resolution
                        br = track.tlbr[2:] / config.resize_to * stream.resolution
                        w, h = br - tl + 1
                        txt.write(f'{mot.frame_count},{track.trk_id},{tl[0]:.6f},{tl[1]:.6f},'
                                    f'{w:.6f},{h:.6f},-1,-1,-1\n')
                    
            # Annotate frame with current detection accuracy (mAP-like metric)
            frame = cv2.putText(frame,f"mAP: {target_accuracy}",(500,20), font, 0.5,(0,0,0),2,cv2.LINE_AA,bottomLeftOrigin=False)
            frame = cv2.putText(frame,f"mAP: {target_accuracy}",(500,20), font, 0.5,(255,255,255),1,cv2.LINE_AA,bottomLeftOrigin=False)

            # If window display is enabled, show the current frame
            if args.show:
                cv2.imshow('Video', frame)
                if cv2.waitKey(1) & 0xFF == 27:
                    break

            # If output URI was specified, write the processed frame
            if args.output_uri is not None:
                stream.write(frame)
finally:
    # Cleanup resources when done or if an error occurs
    if txt is not None:
        txt.close()
    stream.release()
    cv2.destroyAllWindows()

# ------------------- TIMING STATISTICS ------------------- #
# Print average FPS and timing info if MOT was used
if args.mot:
    avg_fps = round(mot.frame_count / prof.duration)
    logger.info('Average FPS: %d', avg_fps)
    mot.print_timing_info()