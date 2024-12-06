import sys
import os
import json
import bpy
import numpy as np
import time
from datetime import datetime
import math

armature = bpy.data.objects.get("Armature")

bone_upper_arm_R = armature.pose.bones.get("J_Bip_R_UpperArm")
bone_lower_arm_R = armature.pose.bones.get("J_Bip_R_LowerArm")
bone_upper_arm_L = armature.pose.bones.get("J_Bip_L_UpperArm")
bone_lower_arm_L = armature.pose.bones.get("J_Bip_L_LowerArm")
bone_spine = armature.pose.bones.get("J_Bip_C_Spine")

# Ensure armature exists
if not armature:
    print("Error: Armature not found.")
    sys.exit(1)

bone_names = ["J_Bip_R_UpperArm", "J_Bip_R_LowerArm", "J_Bip_L_UpperArm", "J_Bip_L_LowerArm", "J_Bip_C_Spine"]
bones = {name: armature.pose.bones.get(name) for name in bone_names}

def euler_to_quaternion(x_angle, y_angle, z_angle):
    """
    Converts Euler angles (in radians) to a quaternion.
    
    Args:
        x_angle (float): Rotation around the X-axis in radians.
        y_angle (float): Rotation around the Y-axis in radians.
        z_angle (float): Rotation around the Z-axis in radians.
    
    Returns:
        tuple: Quaternion as (x, y, z, w).
    """
    # Compute trigonometric values
    cx = math.cos(x_angle / 2)
    cy = math.cos(y_angle / 2)
    cz = math.cos(z_angle / 2)
    sx = math.sin(x_angle / 2)
    sy = math.sin(y_angle / 2)
    sz = math.sin(z_angle / 2)

    # Calculate quaternion components
    w = cx * cy * cz + sx * sy * sz
    x = sx * cy * cz - cx * sy * sz
    y = cx * sy * cz + sx * cy * sz
    z = cx * cy * sz - sx * sy * cz

    return (x, y, z, w)

def setBoneRotation(bone, rotation):
    try:
        bone.rotation_mode = 'QUATERNION'
        #bone.rotation_quaternion[0] = 0.95  # Replace with rotation['w'] if data available
        #bone.rotation_quaternion[1] = rotation['x']
        #bone.rotation_quaternion[2] = rotation['y']
        #bone.rotation_quaternion[3] = rotation['z']
        x,y,z,w = euler_to_quaternion(rotation['x'],rotation['y'],rotation['z'])
        bone.rotation_quaternion[0] = w
        bone.rotation_quaternion[1] = x
        bone.rotation_quaternion[2] = y
        bone.rotation_quaternion[3] = z

    except (KeyError, AttributeError) as e:
        print(f"Error setting rotation for bone {bone.name if bone else 'unknown'}: {e}")

def loadRotationData(filepath="/Users/ryanjewett/Documents/CPE4850/tempdata.json"):
    if not os.path.exists(filepath):
        print(f"File {filepath} not found.")
        return None
    try:
        with open(filepath) as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error loading rotation data: {e}")
        return None

def exportImage(filepath):
    bpy.context.scene.render.image_settings.file_format = 'JPEG'
    bpy.context.scene.render.filepath = filepath
    bpy.ops.render.render(use_viewport=True, write_still=True)

def runRender(count):
    data = loadRotationData()
    
    if data:
        # Apply rotations
        setBoneRotation(bone_upper_arm_R, data["right_shoulder"])
        setBoneRotation(bone_lower_arm_R, data["right_elbow"])
        setBoneRotation(bone_upper_arm_L, data["left_shoulder"])
        setBoneRotation(bone_lower_arm_L, data["left_elbow"])
        setBoneRotation(bone_spine, data["middle_back"])

        # Update the scene to apply transformations
        bpy.context.view_layer.update()

        # Render and export the image
        exportImage(f"/Users/ryanjewett/Documents/CPE4850/SAVE_HERE/simimage{count}.jpeg")
    else:
        print("Failed to load rotation data.")

def clearTempFolder(tempfolder):
    if not os.path.exists(tempfolder):
        print(f"Folder {tempfolder} does not exist.")
        return
    try:
        for item in os.listdir(tempfolder):
            item_path = os.path.join(tempfolder, item)
            if os.path.isfile(item_path):
                os.remove(item_path)
        print(f"Folder {tempfolder} Cleared")
    except Exception as e:
        print(f"Error clearing folder: {e}")

def main():
    path_to_temp_folder = "/Users/ryanjewett/Documents/CPE4850/SAVE_HERE"
    clearTempFolder(path_to_temp_folder)
    status_path = "/Users/ryanjewett/Documents/CPE4850/simstate.json"
    count = 1
    while True:
        try:
            with open(status_path, 'r') as f:
                status = json.load(f)
                if not status[0].get("isrunning", 0):
                    print("Simulation stopped.")
                    break
            runRender(count)
            count += 1
            time.sleep(1)
        except Exception as e:
            print(f"Error in main loop: {e}")
            break

if __name__ == "__main__":
    main()
