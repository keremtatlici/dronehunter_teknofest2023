import cv2
ip = "172.21.73.21"

frame_width = 640
frame_height= 480
screen_size = frame_width*frame_height
font = cv2.FONT_HERSHEY_SIMPLEX
drone_size_percentage=0

telemetry=dict()
liveframe = None


telemetry_socket=None
liveframe_socket=None
missionstart_socket=None
firepermission_socket=None
followto_socket=None

auto_counter= 0