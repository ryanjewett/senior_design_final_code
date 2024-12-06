import re
from flask import Flask, request, jsonify, g
import shutil
import sqlite3
import signal
import datetime
import os
from creatingNewUserDb import creatingNewUser
import json
from datetime import datetime, timedelta

app = Flask(__name__)

conMainDB = sqlite3.connect('main.db',check_same_thread=False)
curMainDB = conMainDB.cursor()

global isCalibrating
isCalibrating = False
global current_user
global conn 
global cur 
global wasThereAnError
wasThereAnError = False
global postureError 
postureError = []
global currentCalData
currentCalData = []
global firstRequest
firstRequest = True

def get_db_connection(db_name):
    try:
        global conn,cur
        conn = sqlite3.connect(db_name, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        print("userdate base connection success")
    except Exception as e:
        app.logger.error(f"Database connection error: {e}")
        conn = None 

def setBaseUser():
    with open('serverinfo.json', 'r') as path:
        data = json.load(path)[0]  

    if data.get('lastlogin') == "":
        get_db_connection(data['defaultuser'])
        print("Setting as Default")
    else:
        get_db_connection(data['lastlogin'])
        print("Setting as Last User")

def setLastLogin(username):
    path = 'serverinfo.json'

    with open(path, 'r') as f:
        data = json.load(f)
    
    data[0]['lastlogin'] = username + '.db'

    with open(path, 'w') as f:
        json.dump(data, f, indent=4)

def generate_timestamps(start_date: str, end_date: str):
    
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    
    timestamps = []
    
    current_date = start
    while current_date <= end:
        for second in range(24 * 60 * 60):  
            time_str = f"{current_date.strftime('%Y-%m-%d')}/{(timedelta(seconds=second) + datetime.min).time()}"
            timestamps.append(time_str)
        current_date += timedelta(days=1)

    return timestamps

def get_data_line(info):
    date, time = info.split('/')
    
    try:
        cur.execute('''
            SELECT Date.date, Time.time, 
                   le.x_value AS left_elbow_x, le.y_value AS left_elbow_y, le.z_value AS left_elbow_z,
                   ls.x_value AS left_shoulder_x, ls.y_value AS left_shoulder_y, ls.z_value AS left_shoulder_z,
                   mb.x_value AS middle_back_x, mb.y_value AS middle_back_y, mb.z_value AS middle_back_z,
                   rs.x_value AS right_shoulder_x, rs.y_value AS right_shoulder_y, rs.z_value AS right_shoulder_z,
                   re.x_value AS right_elbow_x, re.y_value AS right_elbow_y, re.z_value AS right_elbow_z
            FROM Date
            JOIN Time ON Date.id = Time.date_id
            LEFT JOIN Left_Elbow le ON le.time_id = Time.id
            LEFT JOIN Left_Shoulder ls ON ls.time_id = Time.id
            LEFT JOIN Middle_Back mb ON mb.time_id = Time.id
            LEFT JOIN Right_Shoulder rs ON rs.time_id = Time.id
            LEFT JOIN Right_Elbow re ON re.time_id = Time.id
            WHERE Date.date = ? AND Time.time = ?
        ''', (date, time))
        
        data = cur.fetchone()

        if not data:
            print("Message: No data found for the specified date and time.")
            return None

        result = {
            'date': data[0],
            'time': data[1],
            'left_elbow': {
                'x': data[2], 
                'y': data[3], 
                'z': data[4]
            } if data[2] is not None else None,
            'left_shoulder': {
                'x': data[5], 
                'y': data[6], 
                'z': data[7]
            } if data[5] is not None else None,
            'middle_back': {
                'x': data[8], 
                'y': data[9], 
                'z': data[10]
            } if data[8] is not None else None,
            'right_shoulder': {
                'x': data[11], 
                'y': data[12], 
                'z': data[13]
            } if data[11] is not None else None,
            'right_elbow': {
                'x': data[14], 
                'y': data[15], 
                'z': data[16]
            } if data[14] is not None else None
        }

        return result

    except Exception as e:
        print("Error retrieving data from database: " + str(e))
        return None

@app.route('/')
def default():
    app.logger.debug("Debug: / endpoint hit")
    return "OK"

@app.route('/who')
def user_info():
    cur.execute("PRAGMA database_list")
    db_info = cur.fetchall()
    current_db_name = db_info[0][2]
    return f"Current User Database is: {current_db_name}"
   
@app.route('/storageleft')
def get_storage():
    total, used, free = shutil.disk_usage("/")
    return f"Total: {total / (1024 ** 3):.2f} GB, Used: {used / (1024 ** 3):.2f} GB, Free: {free / (1024 ** 3):.2f} GB"

@app.route('/store/<mode>/<date>/<time>/', methods=['POST'])
def store_data(mode, date, time):
    allowed_modes = ["real_data", "calibration_data"]
    global isCalibrating
    global conn
    global cur
    if mode not in allowed_modes:
        return jsonify({"message": "Error: Invalid data collection mode. Use 'real_data' or 'calibration_data'."}), 400
    if isCalibrating:
        isCalibrating = False
        return jsonify({"message":"Calibratoin Request"}), 202      #202 is for calibration request
        
    try:
        data = request.json

        if not isinstance(data, dict):
            return jsonify({"message": "Error: Invalid JSON data format."}), 400
        
        required_parts = ['left_elbow', 'left_shoulder', 'middle_back', 'right_shoulder', 'right_elbow']
        if not all(part in data for part in required_parts):
            return jsonify({"message": "Error: Missing body part data in the request."}), 400
        
        try:

            cur.execute("SELECT id FROM Date WHERE date = ?", (date,))
            row = cur.fetchone()
            
            if row:
                date_id = row[0] 
            else:
                
                cur.execute("INSERT INTO Date (date) VALUES (?)", (date,))
                date_id = cur.lastrowid

            cur.execute("SELECT id FROM Time WHERE time = ? AND date_id = ?", (time, date_id))
            row = cur.fetchone()

            if row:
                time_id = row[0]  
            else:
                cur.execute("INSERT INTO Time (time, date_id) VALUES (?, ?)", (time, date_id))
                time_id = cur.lastrowid

            cur.execute("INSERT INTO Left_Elbow (time_id, x_value, y_value, z_value) VALUES (?, ?, ?, ?)", 
                        (time_id, data['left_elbow']['x'], data['left_elbow']['y'], data['left_elbow']['z']))
            
            cur.execute("INSERT INTO Left_Shoulder (time_id, x_value, y_value, z_value) VALUES (?, ?, ?, ?)", 
                        (time_id, data['left_shoulder']['x'], data['left_shoulder']['y'], data['left_shoulder']['z']))
            
            cur.execute("INSERT INTO Middle_Back (time_id, x_value, y_value, z_value) VALUES (?, ?, ?, ?)", 
                        (time_id, data['middle_back']['x'], data['middle_back']['y'], data['middle_back']['z']))
            
            cur.execute("INSERT INTO Right_Shoulder (time_id, x_value, y_value, z_value) VALUES (?, ?, ?, ?)", 
                        (time_id, data['right_shoulder']['x'], data['right_shoulder']['y'], data['right_shoulder']['z']))
            
            cur.execute("INSERT INTO Right_Elbow (time_id, x_value, y_value, z_value) VALUES (?, ?, ?, ?)", 
                        (time_id, data['right_elbow']['x'], data['right_elbow']['y'], data['right_elbow']['z']))
            
            
            conn.commit()
            return jsonify({"message": "Storage Complete"}), 201
        except Exception as e:
            conn.rollback()
            print(f"An error occurred: " +str(e))
            return jsonify({"message": "Storage Failed: possible Duplicate data"}), 400
       
    except Exception as e:
        return jsonify({"message": f"Error in storage: {str(e)}"}), 500

@app.route('/ret/<mode>/<date>/<time>/', methods=['GET'])
def retrieve_stored_data(mode, date, time):
    allowed_modes = ["real_data", "calibration_data"]
    result = []
    if mode not in allowed_modes:
        return jsonify({"message": "Error: Invalid data collection mode. Use 'real_data' or 'calibration_data'."}), 400

    try:
        cur.execute('''
            SELECT Date.date, Time.time 
            FROM Date
            JOIN Time ON Date.id = Time.date_id
            WHERE Date.date = ? AND Time.time = ?
        ''', (date, time))
        time_data = cur.fetchone()

        result = {
            'date': time_data[0],
            'time': time_data[1],
            'left_elbow': None,
            'left_shoulder': None,
            'middle_back': None,
            'right_shoulder': None,
            'right_elbow': None
        }

        cur.execute('''
            SELECT x_value, y_value, z_value
            FROM Left_Elbow
            JOIN Time ON Left_Elbow.time_id = Time.id
            JOIN Date ON Time.date_id = Date.id
            WHERE Date.date = ? AND Time.time = ?
        ''', (date, time))
        left_elbow_data = cur.fetchone()
        if left_elbow_data:
            result['left_elbow'] = {
                'x': left_elbow_data[0],
                'y': left_elbow_data[1],
                'z': left_elbow_data[2]
            }
        else:
            return jsonify("Message: NULL data detected in retrival - Left_Elbow "), 400

        cur.execute('''
            SELECT x_value, y_value, z_value
            FROM Left_Shoulder
            JOIN Time ON Left_Shoulder.time_id = Time.id
            JOIN Date ON Time.date_id = Date.id
            WHERE Date.date = ? AND Time.time = ?
        ''', (date, time))
        left_shoulder_data = cur.fetchone()
        if left_shoulder_data:
            result['left_shoulder'] = {
                'x': left_shoulder_data[0],
                'y': left_shoulder_data[1],
                'z': left_shoulder_data[2]
            }
        else:
            return jsonify("Message: NULL data detected in retrival - Left_Shoulder "), 400

        cur.execute('''
            SELECT x_value, y_value, z_value
            FROM Middle_Back
            JOIN Time ON Middle_Back.time_id = Time.id
            JOIN Date ON Time.date_id = Date.id
            WHERE Date.date = ? AND Time.time = ?
        ''', (date, time))
        middle_back_data = cur.fetchone()
        if middle_back_data:
            result['middle_back'] = {
                'x': middle_back_data[0],
                'y': middle_back_data[1],
                'z': middle_back_data[2]
            }
        else:
            return jsonify("Message: NULL data detected in retrival - Middle_Back "), 400

        cur.execute('''
            SELECT x_value, y_value, z_value
            FROM Right_Shoulder
            JOIN Time ON Right_Shoulder.time_id = Time.id
            JOIN Date ON Time.date_id = Date.id
            WHERE Date.date = ? AND Time.time = ?
        ''', (date, time))
        right_shoulder_data = cur.fetchone()
        if right_shoulder_data:
            result['right_shoulder'] = {
                'x': right_shoulder_data[0],
                'y': right_shoulder_data[1],
                'z': right_shoulder_data[2]
            }
        else:
            return jsonify("Message: NULL data detected in retrival - Right_Shoulder "), 400

        cur.execute('''
            SELECT x_value, y_value, z_value
            FROM Right_Elbow
            JOIN Time ON Right_Elbow.time_id = Time.id
            JOIN Date ON Time.date_id = Date.id
            WHERE Date.date = ? AND Time.time = ?
        ''', (date, time))
        right_elbow_data = cur.fetchone()
        if right_elbow_data:
            result['right_elbow'] = {
                'x': right_elbow_data[0],
                'y': right_elbow_data[1],
                'z': right_elbow_data[2]
            }
        else:
            return jsonify("Message: NULL data detected in retrival - Right_Elbow "), 400

        #print(result)

        return jsonify(result), 200
                
    except Exception as e:
        return jsonify({"message": f"Error in retrieving data: {str(e)}"}), 500

@app.route('/login', methods=['POST'])           
def checkmaindb():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    try:
        curMainDB.execute('''
            SELECT * FROM Users WHERE username = ? AND password = ?
            ''', (username, password))
        user = curMainDB.fetchone()
    except Exception as e:
        app.logger.error(f"Error during login check: {str(e)}")
        print(str(e))
        return jsonify({"message": f"Error during login check: {str(e)}"}), 500
    print(user)
    if user is None:
        return jsonify({"message": "Invalid username or password."}), 401
    else:
        global current_user
        current_user = (f"{username}.db") 
        get_db_connection(f"{username}.db")
        setLastLogin(username)
        return jsonify({"message": "Login successful!"}), 200

@app.route('/reg', methods=['POST'])
def registernewuser():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    try:
        newUser = creatingNewUser()
        newUser.newuser(username, password)
        newUser.closeConnection()
        global current_user
        current_user = (f"{username}.db")
        get_db_connection(f"{username}.db")
        setLastLogin(username)
        return jsonify({"message": "New User Created"}), 200

    except Exception as e:
        return jsonify({"message": f"Error in creating new user db: {str(e)}"}), 401
    
@app.route('/getchk/<mode>/<date1>/<date2>', methods = ['GET'])
def data_chunk_generator(mode, date1, date2):
    returnlist = []
    allowed_modes = ["real_data", "calibration_data"]
    
    if mode not in allowed_modes:
        return jsonify({"message": "Error: Invalid data collection mode. Use 'real_data' or 'calibration_data'."}), 400
    
    timelist = generate_timestamps(date1, date2)

    for datetime in timelist:
        lineinfo = get_data_line(datetime)
        
        if lineinfo is None:
            print(f"No data found at: {datetime}")
        else:
            returnlist.append({
                                "timestamp": datetime,
                                "left_elbow": {"x": lineinfo['left_elbow']['x'], "y": lineinfo['left_elbow']['y'], "z": lineinfo['left_elbow']['z']},
                                "left_shoulder": {"x": lineinfo['left_shoulder']['x'], "y": lineinfo['left_shoulder']['y'], "z": lineinfo['left_shoulder']['z']},
                                "middle_back": {"x": lineinfo['middle_back']['x'], "y": lineinfo['middle_back']['y'], "z": lineinfo['middle_back']['z']},
                                "right_shoulder": {"x": lineinfo['right_shoulder']['x'], "y": lineinfo['right_shoulder']['y'], "z": lineinfo['right_shoulder']['z']},
                                "right_elbow": {"x": lineinfo['right_elbow']['x'], "y": lineinfo['right_elbow']['y'], "z": lineinfo['right_elbow']['z']}
                            })
    return jsonify(returnlist), 200

@app.route('/postureER', methods=['POST'])
def user_posture_error():
    global postureError
    global wasThereAnError
    try:
        wasThereAnError = True
        postureError = request.get_json()
        return jsonify({'message': 'good error post'}), 200
    except Exception as e:
        print(str(e))
        return jsonify({'message': 'bad error post'}), 400

@app.route('/geter', methods = ['GET'])
def getting_current_error():
    global wasThereAnError
    global postureError
    data = []
    if wasThereAnError:
        data = postureError  #error code 0 is no error, 1 is left_shoulder, 2 is middle_back, 3 is right_shoulder
    else:
        data = [{'left_shoulder': 0, 'middle_back': 0, 'right_shoulder':0}]
    wasThereAnError = False
    return jsonify(data), 200

@app.route('/cal',methods = ['GET'])
def calibrate():
    try:
        global isCalibrating
        isCalibrating = True

        return jsonify({"message":"Calibrating starting"}), 200
    except:
        return jsonify({"message":"Error in starting calibration"}), 400

@app.route('/caldata', methods = ['POST'])
def store_calibartion():
    try:
        global currentCalData
        currentCalData = None
        data = request.get_json()
        currentCalData = data
        return jsonify({'Message': 'success in storing cal data'}), 200
    except Exception as e:
        print(f"error in caldata: {str(e)}")
        return jsonify({'message':'error in storing calibration data'}), 400

@app.route('/time', methods = ['GET'])
def whatTime():
    try:
        time = datetime.now()
        date = time.date()
        real_time = time.strftime('%H:%M:%S')
        return jsonify({"message":f"{date}/{real_time}"}), 200
    except Exception as e:
        print(str(e))
        return jsonify({"message":"bad time call"}), 400

@app.route('/kill')
def terminate_server():
    os.kill(os.getpid(), signal.SIGINT)
    return "done"

@app.before_request
def serverFirstRun():
    global firstRequest
    if firstRequest: 
        setBaseUser()
    firstRequest = False

@app.teardown_appcontext
def close_db_connection(exception):
    conn = g.pop('conn', None)
    if conn is not None:
        conn.close()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)


#104.190.219.231/5000

    
