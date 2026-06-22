Explanation document:
This Splunk app is developed by Beijing Weibu Online Technology Co., Ltd. and is suitable for data integration between Splunk and Threat Intelligence Platform (TIP):
1、 Installation
    In the Splunk web page, go to Manage Applications ->Local File Installation, select Threatbook TIP. tar. gz, 
    install and restart Splunk.

2、 Users need to configure the following information in the configuration:
    1. TIP related configurations
        1.1 First, enter the basic configuration page and fill in the information

        1.2 Basic Configuration Filling Example
            Splunk address: 127.0.0.1:8089 (Splunk address for connecting to the local machine, proto, can be empty)
            User name: test
            Password: 123456
        
        1.3 Example of IP Reputation Check Filling
            Index name (input): test_in (indicating to read data from this index)
            Index name (output): testouts (indicating the output of collision intelligence data to this index)
            Intelligence query interface: http://xx.xx.xx.xx:8090/tip_api/v4/ip
            APIKEY:  (TIP Platform Other ->Business Settings ->KEY)
        
        1.4 Example of filling out collapse detection
            Index name (input): test_in (indicating to read data from this index)
            Index name (output): testouts (indicating the output of collision intelligence data to this index)
            Intelligence query interface: http://xx.xx.xx.xx:8090/tip_api/v4/dns
            APIKEY:  (TIP Platform Other ->Business Settings ->KEY)

    Attention: The above information is mandatory, and the input index and output index must be ensured to exist before filling in.   

3、 Display:
    The backend of this app will execute scheduled tasks at regular intervals (every 10 minutes). The scheduled task reads the input index from the configuration information, performs intelligence collision, and outputs it to the output index.
    The original combination of intelligence and logs after successful collision will be displayed as JSON on the IP Reputation Detection and IOC Detection pages, respectively. The display content includes post collision
    The list information and the aggregated information of each field dimension.



说明文档:

本splunk app 由 北京微步在线科技有限公司 开发，适用于 splunk 与  Threat Intelligence Platform 平台(以下简称TIP)数据对接:
一、安装
    在 splunk web 页面中， 从管理应用->本地文件安装，选中Threatbook-TIP.tar.gz，安装并重新启动splunk。
    
二、使用者需要在配置中，配置以下信息:
    1.TIP的相关配置
        1.1 首先进入基础配置页面，进行信息的填写

        1.2 基本配置填写样例
            splunk地址：127.0.0.1:8089（连接本机的splunk地址，proto,可为空）  
            用户名: test
            密码： 123456

        1.3 IP信誉检测填写样例
            索引名称（输入）：test_in （表示要从该索引中读取数据）
            索引名称（输出）：test_out（表示碰撞情报后的数据输出到该索引）
            情报查询接口： http://xx.xx.xx.xx:8090/tip_api/v4/ip
            APIKEY：(TIP 平台 其他->业务设置->KEY)
        
         1.4 失陷检测填写样例
            索引名称（输入）：test_in （表示要从该索引中读取数据）
            索引名称（输出）：test_out（表示碰撞情报后的数据输出到该索引）
            情报查询接口： http://xx.xx.xx.xx:8090/tip_api/v4/dns
            APIKEY：(TIP 平台 其他->业务设置->KEY)

    注意事项：以上信息均为必填项，输入索引、输出索引需要在填写前保证存在。
                
三、展示：        
    本app 后台会自行间隔(每10分钟)执行定时任务。定时任务进去读取配置信息中的输入索引，进行情报碰撞，输出到输出索引中。
    碰撞成功后的情报和日志原文组合为json会在IP Reputation Detection和IOC Detection页面分别展示。展示内容包括碰撞后
    的列表信息以及各字段维度的聚合信息。
        

    




