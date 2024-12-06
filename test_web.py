from urllib import response
import requests
import datetime

now = datetime.datetime.now()
#current_date = now.date()
#current_time = now.strftime("%H:%M:%S")
current_date = "2024-10-10"
current_time = "10:10:10"
base_url = 'http://localhost:5000'

def test_login():
    logininfo = {
        "username": 'test5',
        "password": 'test5'
    }
    response = requests.post(f"{base_url}/login", json=logininfo)
    print(f"Login response:", response.text)
    assert response.status_code == 200, "Login failed"

def test_index():
    response = requests.get(f'{base_url}/')
    print('Index Route Status:', response.text)

def test_help():
    response = requests.get(f'{base_url}/help')
    print('Help Route Status:', response.text)

def test_storage_left():
    response = requests.get(f'{base_url}/storageleft')
    print('Storage Left Route Status:', response.text)

def test_store_data():
    testData = { "left_elbow": {"x": 1, "y": 1, "z": 1},
                 "left_shoulder": {"x": 1, "y": 1, "z": 1},
                 "middle_back": {"x": 1, "y": 1, "z": 1},
                 "right_shoulder": {"x": 1, "y": 1, "z": 1},
                 "right_elbow": {"x": 1, "y": 1, "z": 1}}
    response = requests.post(f'{base_url}/store/real_data/{current_date}/{current_time}/', json=testData)
    print(f'Store Data Route Status with :', response.text)

def test_retrieve_data():
    response = requests.get(f'{base_url}/ret/real_data/{current_date}/{current_time}/')
    print(f'Retrieve Data Route Status for :', response.json())

def test_data_chk():
    response = requests.get(f"{base_url}/getchk/real_data/{current_date}/{current_date}")
    print(f'Retrieve Data Route Status for chk :', response.json())

if __name__ == '__main__':
    test_login()
    test_index()
    test_help()
    test_storage_left()
    test_store_data()
    test_retrieve_data()
    test_data_chk()
