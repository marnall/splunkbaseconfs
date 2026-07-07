
# encoding = utf-8

import os
import sys
import time
import datetime
import socket
import struct 

names = ["IsRaceOn", "TimestampMS", "EngineRpmMax", "EngineRpmIdle", "EngineRpmCurrent", "AccelerationX", "AccelerationY", "AccelerationZ", "VelocityX", "VelocityY", "VelocityZ", "AngularVelocityX", "AngularVelocityY", "AngularVelocityZ", "Yaw", "Pitch", "Roll", "NormalizedSuspensionTravelFrontLeft", "NormalizedSuspensionTravelFrontRight", "NormalizedSuspensionTravelRearLeft", "NormalizedSuspensionTravelRearRight", "TireSlipRatioFrontLeft", "TireSlipRatioFrontRight", "TireSlipRatioRearLeft", "TireSlipRatioRearRight", "WheelRotationSpeedFrontLeft", "WheelRotationSpeedFrontRight", "WheelRotationSpeedRearLeft", "WheelRotationSpeedRearRight", "WheelOnRumbleStripFrontLeft", "WheelOnRumbleStripFrontRight", "WheelOnRumbleStripRearLeft", "WheelOnRumbleStripRearRight", "WheelInPuddleDepthFrontLeft", "WheelInPuddleDepthFrontRight", "WheelInPuddleDepthRearLeft", "WheelInPuddleDepthRearRight", "SurfaceRumbleFrontLeft", "SurfaceRumbleFrontRight", "SurfaceRumbleRearLeft", "SurfaceRumbleRearRight", "TireSlipAngleFrontLeft", "TireSlipAngleFrontRight", "TireSlipAngleRearLeft", "TireSlipAngleRearRight", "TireCombinedSlipFrontLeft", "TireCombinedSlipFrontRight", "TireCombinedSlipRearLeft", "TireCombinedSlipRearRight", "SuspensionTravelMetersFrontLeft", "SuspensionTravelMetersFrontRight", "SuspensionTravelMetersRearLeft", "SuspensionTravelMetersRearRight", "CarOrdinal", "CarClass", "CarPerformanceIndex", "DrivetrainType", "NumCylinders", "PositionX", "PositionY", "PositionZ", "Speed", "Power", "Torque", "TireTempFrontLeft", "TireTempFrontRight", "TireTempRearLeft", "TireTempRearRight", "Boost", "Fuel", "DistanceTraveled", "BestLap", "LastLap", "CurrentLap", "CurrentRaceTime", "LapNumber", "RacePosition", "Accel", "Brake", "Clutch", "HandBrake", "Gear", "Steer", "NormalizedDrivingLine", "NormalizedAIBrakeDifference"]

def validate_input(helper, definition):
    pass

def collect_events(helper, ew):
    opt_ip = helper.get_arg('ip')
    opt_port = int(helper.get_arg('port'))
    opt_enabled_metrics = [int(m) for m in helper.get_arg('enabled_metrics')]
    opt_rate_limit = float(helper.get_arg('rate_limit'))/1000 
    
    helper.log_info("Time is: {}".format(time.time()))

    helper.log_info("Rate Limit: {}s".format(opt_rate_limit))
    
    helper.log_info("Metrics Enabled: {}".format(", ".join([names[m] for m in opt_enabled_metrics])))
    
    helper.log_info("Opening UDP: {}:{}".format(opt_ip,opt_port))
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((opt_ip,opt_port))
    
    lasttime = 0

    while True:
        data, addr = sock.recvfrom(512)
        now = time.time()
        if now >= (lasttime+opt_rate_limit):
            lasttime = now
            size = len(data)
            helper.log_debug("Received {} bytes from {}".format(size,addr))
            if(size == 324): #Forza Horizon 
                count = 85
                values = struct.unpack('<i I 27f 4i 20f 5i 12x 17f H 6B 3b x',data)
            elif (size == 311): #Forza Motorsport 7 Dash mode
                count = 85
                values = struct.unpack('<i I 27f 4i 20f 5i 17f H 6B 3b',data)
            elif (size == 231): #Forza Motorsport 7 Sled mode
                count = 58
                values = struct.unpack('<i I 27f 4i 20f 5i',data)
            else: #Unrecognised UDP packet length
                continue 
            
            helper.log_debug("Extracted {} values".format(len(values)))
            
            for m in opt_enabled_metrics:
                if m < count:
                    raw = "{}:{}|{}".format(names[m],values[m],("c","g")[m==70])
                    ew.write_event(helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), host=addr[0], data=raw))
