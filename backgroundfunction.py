import requests
import os
import json
import datetime
import subprocess
import psutil

base_url = 'http://127.0.0.1:5000'

def loginCredValidation(username, password):
    data = {
        "username": username,
        "password": password
    }
    try:
        response = requests.post(f"{base_url}/login", json=data)
        #response.raise_for_status()  
    except requests.RequestException as e:
        print(f"Request failed: {str(e)}")
        return False
    
    if response.status_code == 200:
        return True
    else:
        print(f"Login failed with status code {response.status_code}: {response.text}")
        return False
    
def registerNewUser(username,password):
    data = {
        "username": username,
        "password": password
    }

    response = requests.post(f"{base_url}/reg", json=data)

    if response.status_code == 200:
        return True
    else:
        return False
    
def connectToServer():
    try:
        response = requests.get(f"{base_url}/")
        if response.text == "OK":
            return True
        else:
            return False
    except requests.RequestException as e:
        print(e)
        return False

def retriveDataChunk(date1,date2):

    tempfile = 'tempfile.json'

    if os.path.exists(tempfile):
        os.remove(tempfile)

    try:
        response = requests.get(f"{base_url}/getchk/real_data/{date1}/{date2}")
        response.raise_for_status()
        data = response.json()
        with open(tempfile, 'w') as f:
            json.dump(data,f, indent=4)
        return True
    except Exception as e:
        print("Error in retriving data chunk: "+ str(e))
        return False

def saveCurrentTempFile():
    try:
        now = datetime.datetime.now()
        currentDate = now.strftime("%Y-%m-%d")
        currentTime = now.strftime("%H-%M-%S")
        
        fileSave = f"saved_data_{currentDate}_{currentTime}.json"

        current_dir = os.getcwd()
        savepath = os.path.join(current_dir,fileSave)
        if os.path.exists(savepath):
            return False

        with open('tempfile.json', 'r') as f:
            data = json.load(f)
        
        with open(fileSave, 'w') as f:
            json.dump(data, f, indent=4)
        return True
    except Exception as e:
        print(f"Error in saving data: {str(e)}")
        return False
    
def requestCalibration():
    try:
        response = requests.get(f"{base_url}/cal")
    except requests.RequestException as e:
        print(f"Request failed: {str(e)}")
        return False
    
    if response.status_code == 200:
        return True
    else:
        return False
    
def is_blender_running():
    for process in psutil.process_iter(['name']):
        if process.info['name'] == 'Blender':
            return True
    return False

def startUpBlender():
    blender_executable = "/Applications/Blender.app/Contents/MacOS/Blender"
    blender_file = "Low_Poly_Man6.blend"
    python_script = "blenderscript7.py"
    current_directory = os.getcwd()
    
    blend_file_path = os.path.join(current_directory, blender_file)
    python_script_path = os.path.join(current_directory, python_script)
    
    if os.path.exists(blend_file_path):
        if os.path.exists(python_script_path):
            #if not is_blender_running():         #disabled chekc for blender rerun
                
                subprocess.Popen([blender_executable, blend_file_path,"--background", "--python", python_script_path])
                return True
            #else:
            #    print("Blender is already running!")
            #    return False
        else:
            print(f"{python_script_path} not found!")
            return False
    else:
        print(f"{blend_file_path} not found!")
        return False

def clearTempFolder(tempfolder):
        try:
            for item in os.listdir(tempfolder):
                item_path = os.path.join(tempfolder, item)
                if os.path.isfile(item_path):
                    os.remove(item_path)
            print(f"Folder {tempfolder} Cleared")
            return True
        except Exception as e:
            print(f"Error occurred: {e}")
            return False
