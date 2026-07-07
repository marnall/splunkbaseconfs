import pvxml
import time
import json
import os
import sys

PVX_ACCEDIAN_PARAMS = [sys.argv[2], sys.argv[3], int(sys.argv[4])]


MODEL_FILENAME = os.path.dirname(os.path.abspath(__file__))+'/if_nt_200_0.01.joblib'
#print(MODEL_FILENAME)
def check_for_alert(prediction):
    chunk_size = len(prediction) // 10
    alert_threshold = len(prediction) // 20
    
    for i in range(len(prediction) - chunk_size):
    	malicious_packets = sum([1 for j in range(i, i + chunk_size) if prediction[j] == -1])
    	if malicious_packets > alert_threshold:
    		return (i, i + chunk_size) # return position where alert occured
    		
    return None

def on_prediction_result(packets, prediction):
    malicious_packets = sum([1 for p in prediction if p == -1])
    malicious_rate = (malicious_packets / len(prediction)) * 100
 
    #log_str = '{} - {} packets - {:.3f}% malicious'.format(time.time(), len(packets), malicious_rate)

    

    alert_result = check_for_alert(prediction)
    if alert_result != None:
        #print('>>>>>>>>>> Alert! Pay your attention! Alert! <<<<<<<<<<')

        conversations, users, trees = {'src_ip': [], 'dest_ip': []}, [], []
        for i in range(alert_result[0], alert_result[1]):
            if prediction[i] == -1:
                if packets[i]['src_ip'] != 0 and packets[i]['dest_ip'] != 0:
                    is_present = False
                    for j in range(len(conversations['src_ip'])):
                        if conversations['src_ip'][j] == packets[i]['src_ip'] and conversations['dest_ip'][j] == packets[i]['dest_ip']:
                            is_present = True
                            break
                    if not is_present:
                        conversations['src_ip'].append(packets[i]['src_ip'])
                        conversations['dest_ip'].append(packets[i]['dest_ip']) 
                
                if packets[i]['user'] != 0:
                	users.append(packets[i]['user'])
                if packets[i]['tree'] != 0:
                        trees.append(packets[i]['tree'])
        
        users = list(set(users))
        trees = list(set(trees))
        table = {'isalert':'True','conversations': conversations, 'users': users, 'trees': trees}
        print(json.dumps(table))
    else:
        log_info = {'isalert':'False','pakets_count':len(packets)}
        print(json.dumps(log_info))
            
grabber = pvxml.SMBGrabber(*PVX_ACCEDIAN_PARAMS)
predictor = pvxml.SMBPredictor(grabber, MODEL_FILENAME)
predictor.real_time_predict(on_prediction_result)
