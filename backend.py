import ast
import json
import subprocess
from flask import Flask, request, render_template, jsonify
import requests
import pandas as pd
from io import StringIO
import re

app = Flask(__name__)

def get_kube_token():
    try:
        with open("/home/harold/Desktop/web/certificates/token.txt", "r") as file:
            token = file.read().strip()
        return token
    except Exception as e:
        print("Error reading Kubernetes token:", e)
        return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process_data', methods=['POST'])
def process_data():
    data = request.json
    print("Received data:", data)
    kube_token = get_kube_token()
    if kube_token:
        url = "https://192.168.115.133:6443/api/v1/namespaces/kube-system/pods/ovn-central-5d46bd57c8-gmrtx/exec"
        headers = {
            "Sec-WebSocket-Key": "SGVsbG8sIHdvcmxkIQ==",
            "Sec-WebSocket-Version": "13",
            "Connection": "Upgrade",
            "Upgrade": "websocket",
            "Accept-Charset": "utf-8",
            "Authorization": f"Bearer {kube_token}",
        }

        params = {
            "container": "ovn-central",
            "stdin": "1",
            "stdout": "1",
            "stderr": "1",
            "tty": "1",
            "command": ["ovn-nbctl", "show"],
        }

        try:
            response = requests.get(url, headers=headers, params=params, verify="/home/harold/Desktop/web/certificates/ca.crt", allow_redirects=False)
        
            print("Kết quả lệnh:", response.text)
            return jsonify(response.text)
        except Exception as e:
            print("Error making request to Kubernetes API:", e)
            return jsonify({"message": "Error making request to Kubernetes API", "error": e})
    else:
        return jsonify({"message": "Error getting Kubernetes token"})

@app.route('/process_data_bash', methods=['POST'])
def process_data_bash():

    data = request.json
   
    print("Received data:", data)
    kube_token = get_kube_token()
    if kube_token:
        try: 
            result = subprocess.check_output(['bash', '/home/harold/Desktop/web/execute.sh'], stderr=subprocess.STDOUT, text=True)
            key_value_pairs = [item.split(': ', 1) for item in result.strip().split('\n')]
            formatted_dict = {key.strip(): value.strip() for key, value in key_value_pairs}
            t = formatted_dict.get('bandwidth_min')
            # Chuyển đổi từ điển thành định dạng JSON
            #json_result = json.dumps(formatted_dict, indent=2)

            return result.strip()
        except subprocess.CalledProcessError as e:
            # Xử lý lỗi nếu có
            return f"Error: {e.output.strip()}"

    else:
        return jsonify({"message": "Error getting Kubernetes token"})

@app.route('/create_pod', methods=['POST'])
def create_pod():
    data = request.get_json()
    event = "CREATE-POD"
    pod_name = data.get('podName', '')
    node_name = data.get('nodeName', '')

    # Chuẩn bị lệnh để thực thi
    command = f'POD_NAME={pod_name} NODE_NAME={node_name} EVENT={event} /home/harold/Desktop/web/execute.sh'    # Thực thi file .sh
    try:
        result = subprocess.run(command, shell=True, stderr=subprocess.STDOUT, text=True, stdout=subprocess.PIPE)
        if result.stdout.strip() == 'true':
            return jsonify({'status': 'success', 'result': 'true'})
        else:
            return jsonify({'status': 'fail', 'result': 'false'})

    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")

@app.route('/list_pods', methods=['GET'])
def list_pod():
    event = "LIST-POD"
    # Chuẩn bị lệnh để thực thi
    command = f'EVENT={event} /home/harold/Desktop/web/execute.sh'    # Thực thi file .sh
    try:
        result = subprocess.run(command, shell=True, stderr=subprocess.STDOUT, text=True, stdout=subprocess.PIPE)
        df = pd.read_csv(StringIO(result.stdout), delim_whitespace=True, header=None, on_bad_lines='skip')
        # In DataFrame
        print(df)

    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
    return jsonify({'status': 'success', 'result': df.to_dict(orient='records')})

@app.route('/list_nodes', methods=['GET'])
def list_nodes():
    event = "LIST-NODE"
    # Chuẩn bị lệnh để thực thi
    command = f'EVENT={event} /home/harold/Desktop/web/execute.sh'    # Thực thi file .sh
    try:
        result = subprocess.run(command, shell=True, stderr=subprocess.STDOUT, text=True, stdout=subprocess.PIPE)
        list_nodes = [node for node in result.stdout.strip().splitlines() if node]
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
    return jsonify({'status': 'success', 'result': list_nodes})

@app.route('/create_qos', methods=['POST'])
def create_qos():
    data = request.get_json()
    event = "CREATE-QOS"
    podNameSource = data.get('podNameSource', '')
    podNameDestination = data.get('podNameDestination', '')
    min = data.get('min', '')
    max = data.get('max', '')

    # Chuẩn bị lệnh để thực thi
    command = f'POD_NAME_SOURCE={podNameSource} POD_NAME_DESTINATION={podNameDestination} MIN={min} MAX={max} EVENT={event} /home/harold/Desktop/web/execute.sh'    # Thực thi file .sh
    try:
        result = subprocess.run(command, shell=True, stderr=subprocess.STDOUT, text=True, stdout=subprocess.PIPE)
        if result.stdout.strip() == 'true':
            return jsonify({'status': 'success', 'result': 'true'})
        else:
            return jsonify({'status': 'success', 'result': result.stdout.strip()})

    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        return jsonify({'status': 'fail', 'result': e.stderr})
    
@app.route('/list_pods_kube_ovn', methods=['GET'])
def list_pod_kube_ovn():
    event = "LIST-POD-KUBE-OVN"
    # Chuẩn bị lệnh để thực thi
    command = f'EVENT={event} /home/harold/Desktop/web/execute.sh'    # Thực thi file .sh
    try:
        result = subprocess.run(command, shell=True, stderr=subprocess.STDOUT, text=True, stdout=subprocess.PIPE)
      
        # Loại bỏ các ký tự trắng ở đầu và cuối mỗi mục
        entries = re.split(r'\n*_uuid\s*:', result.stdout)[1:]
        entries = [entry.strip() for entry in entries]

        # Xử lý mỗi mục thành đối tượng JSON
        json_raw = []
        for entry in entries:
            # Thêm '_uuid' vào đầu mỗi mục để đảm bảo định dạng đúng
            entry = '_uuid:' + entry
            try:
                entry_dict = dict(item.split(':', 1) for item in entry.split('\n') if item)
                json_raw.append(entry_dict)
            except ValueError as e:
                print(f"Error processing entry: {e}")

        # In ra đối tượng JSON hoặc lưu vào một tệp
        json_data = format_json(json_raw)
        list_pod = []
        for i in json_data:
            external_ids_str = i['external_ids']
            matches = re.findall(r'(\w+)="(.*?)"', external_ids_str)

            # Tạo từ điển từ các kết quả trích xuất
            external_ids_dict = {key: value for key, value in matches}

            pod_value = external_ids_dict.get('pod', '')
            if pod_value != "": 
                list_pod.append(i['name'].split(".")[0]) 
        return jsonify({'status': 'success', 'result': list_pod})
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
    #return jsonify({'status': 'success', 'result': df.to_dict(orient='records')}
        
@app.route('/list_queue', methods=['GET'])
def list_queue():
    event = "LIST-QUEUES"
    # Chuẩn bị lệnh để thực thi
    a = list_pod_kube_ovn().json
    list_pods = a['result']
    result_objects = []
    for pod in list_pods:
        command = f'EVENT={event} POD_NAME_DESTINATION={pod} /home/harold/Desktop/web/execute.sh'
        result = subprocess.run(command, shell=True, stderr=subprocess.STDOUT, text=True, stdout=subprocess.PIPE)
        matches = re.findall(r'to-lport\s+(\d+)\s+\(inport=="([^"]+)"\)\s+min=(\d+)\s+rate=(\d+)', result.stdout)

        for match in matches:
            inport, min_val, rate = match[1], int(match[2]), int(match[3])
            result_objects.append({
                'pod destination': pod,
                'pod source': inport.replace('.kube-system', ''),
                'min': min_val,
                'rate': rate
            })
    return jsonify({'status': 'success', 'result': result_objects})

def format_json(data):
    formatted_data = []
    for entry in data:
        formatted_entry = {}
        for key, value in entry.items():
            formatted_entry[key.strip()] = value.strip()
        formatted_data.append(formatted_entry)
    return formatted_data

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=True)

