#-*-coding:utf-8-*-
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import json
import splunk
import splunk.rest
import splunk.bundle
import splunklib.client as client


# 0 set_response(self.response, {'error': 'splunk服务连接异常'}, 400)
# 1 set_response(self.response, {'error': '输入索引不存在'}, 400)
# 2 set_response(self.response, {'error': '输出索引不存在'}, 400)

def set_response(response, body, status=200):
    response.setHeader('content-type', 'application/json')
    response.setStatus(status)
    response.write(json.dumps(body))
    

# splunk服务连接与索引检查
def connect_splunk(host, port, username, password, inputindex, outputindex):
     #读取输入索引的数据进行分析
    try:
        service = client.connect(
        host=host,
        port=port,
        username=username,
        password=password
        )
    except:
        return 0
    #判断输入、输出索引是否存在
    indexes = service.indexes
    if inputindex not in indexes:       
        return 1
    if outputindex not in indexes:
        return 2
    return service
    

class ApiUrl(splunk.rest.BaseRestHandler):
    def handle_GET(self):
        conf = splunk.bundle.getConf('application', self.sessionKey, owner='nobody')['config']
        try:
            splunk_url = conf['splunk_url']
            username = conf['username']
            password = conf['password']
            inbound_inputindex = conf['inbound_inputindex']
            inbound_outputindex = conf['inbound_outputindex']
            inbound_url = conf['inbound_url']
            inbound_apikey = conf['inbound_apikey']
            outbound_inputindex = conf['outbound_inputindex']
            outbound_outputindex = conf['outbound_outputindex']
            outbound_url = conf['outbound_url']
            outbound_apikey = conf['outbound_apikey']
            lang = conf['lang']
        except:
           splunk_url = ""
           username = ""
           password  = ""
           inbound_inputindex = ""
           inbound_outputindex =""
           inbound_url =""
           inbound_apikey = ""
           outbound_inputindex = "" 
           outbound_outputindex = ""
           outbound_url = ""
           outbound_apikey = ""
           lang = ""
        set_response(self.response, {'splunk_url':splunk_url, 
        'username':username, 'password':password, 'inbound_inputindex':inbound_inputindex,
         'inbound_outputindex':inbound_outputindex, 'inbound_url':inbound_url, 'inbound_apikey':inbound_apikey,
         'outbound_inputindex':outbound_inputindex, 'outbound_outputindex':outbound_outputindex, 'outbound_url':outbound_url,
          'outbound_apikey':outbound_apikey,'lang':lang})


    def handle_POST(self):
        splunk_url = self.args.get('splunk_url')
        username = self.args.get('username')
        password = self.args.get('password')
        lang = self.args.get('lang')
        if not (splunk_url and username and password):
            set_response(self.response, {'error': 'Basic configuration parameters are mandatory'}, 400)
            return
        if ':' not in splunk_url:
            set_response(self.response, {'error': 'Splunk_URL filling does not meet the specifications'}, 400)
            return 
        host_port = splunk_url.strip().rsplit(':', 1)
        host = host_port[0]
        port = host_port[1]

        # 获取入站时间戳字段
        conf = splunk.bundle.getConf('application', self.sessionKey, owner='nobody')['config']

        # 入站配置
        inbound_inputindex = self.args.get('inbound_inputindex')
        inbound_outputindex = self.args.get('inbound_outputindex')
        inbound_url = self.args.get('inbound_url')
        inbound_apikey = self.args.get('inbound_apikey')
        # 入站配置项都不为空，则进行索引读取操作
        if inbound_inputindex and inbound_outputindex and inbound_url and inbound_apikey:
            #读取输入索引的数据进行分析
            in_service = connect_splunk(host, port, username, password, inbound_inputindex, inbound_outputindex)              
            if in_service == 0:
                set_response(self.response, {'error': 'Splunk service connection exception'}, 400)
                return
            elif in_service == 1:
                set_response(self.response, {'error': 'The input index does not exist in the inbound configuration'}, 400)
                return
            elif in_service == 2:
                set_response(self.response, {'error': 'The output index does not exist in the inbound configuration'}, 400)
                return

        #出站配置
        outbound_inputindex = self.args.get('outbound_inputindex')
        outbound_outputindex = self.args.get('outbound_outputindex')
        outbound_url = self.args.get('outbound_url')
        outbound_apikey = self.args.get('outbound_apikey')
        
        # 出站配置项都不为空，则进行索引读取操作
        if outbound_inputindex and outbound_outputindex and outbound_url and outbound_apikey:
            outservice = connect_splunk(host, port, username, password, outbound_inputindex, outbound_outputindex)              
            if outservice == 0:
                set_response(self.response, {'error': 'Splunk service connection exception'}, 400)
                return
            elif outservice == 1:
                set_response(self.response, {'error': 'The input index does not exist in the outbound configuration'}, 400)
                return
            elif outservice == 2:
                set_response(self.response, {'error': 'The output index does not exist in the outbound configuration'}, 400)
                return
            
        bun = splunk.bundle.getConf('application', self.sessionKey, owner='nobody')
        bun.beginBatch()
        conf = bun['config']
        conf['splunk_url'] = splunk_url
        conf['username'] = username
        conf['password'] = password
        conf['inbound_inputindex'] = inbound_inputindex
        conf['inbound_outputindex'] = inbound_outputindex
        conf['inbound_url'] = inbound_url
        conf['inbound_apikey'] = inbound_apikey     
        conf['outbound_inputindex'] = outbound_inputindex
        conf['outbound_outputindex'] = outbound_outputindex
        conf['outbound_url'] = outbound_url
        conf['outbound_apikey'] = outbound_apikey
        conf['lang'] = lang
        bun.commitBatch()
        set_response(self.response, {"ok": "setting success!"})