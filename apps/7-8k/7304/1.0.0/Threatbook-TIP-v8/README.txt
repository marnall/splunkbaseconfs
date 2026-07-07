说明文档:

本splunk app 由 北京微步在线科技有限公司 开发，适用于 splunk 与  Threat Intelligence Platform 平台(以下简称TIP)数据对接:

特别说明:
    本app 会根据配置，间断的索引splunk日志，会使用一定量的 splunk查询量，请注意splunk的池配额和使用量。


一、安装
    在 splunk web 页面中， 从管理应用->本地文件安装，选中TIP.tar.gz，安装并重新启动splunk。
    
二、使用者需要在配置中，配置以下信息:
    1.TIP的相关配置
        1.1 TIP URL(例如:http://127.0.0.1:9001)
        1.2 TIP APIKEY(TIP 平台 其他->业务设置->KEY)
        如果您没有购买TIP平台服务，可以邮件联系contactus@threatbook.cn 试用。

    2.Splunk 搜索设置
        需要配置您的splunk 搜索语法，搜索你需要查询IOC(可为ip或者域名),

        本app 后台会自行间隔(每2分钟)的索引。并且需要记录时间戳(ts)、目标地址或域名(dest)、源地址(src)、协议（proto,可为空）,所以和您配置分部分最终会形成如下是搜索语句:
        'search * _indextime > %d _indextime <= %d index=*' + 您的配置 +'| fields ts,dest,src,proto'
        请您新根据日志格式，搜索并声明为对应的字段，否则无法使用。

    3.代理，如果splunk 与tip 无法进行网络通信，可以使用代理配置。

    



三、输出结果：

    app 会将查询结果,保存以下信息(字段-值对应)在splunk中，示例如下:

    ts=1528108497
    src=172.16.100.125:2388
    dest=pgaeyqcvkdetaysgqwhrwe.biz
    intel_type=zeus,c2
    proto=telnet
    now=[{u'confidence': 75, u'source_name': u'\u5fae\u6b65\u5728\u7ebf-\u673a\u8bfb\u60c5\u62a5', u'data': u'pgaeyqcvkdetaysgqwhrwe.biz', u'type': u'zeus'}, {u'confidence': 75, u'source_name': u'\u5fae\u6b65\u5728\u7ebf-\u673a\u8bfb\u60c5\u62a5', u'data': u'pgaeyqcvkdetaysgqwhrwe.biz', u'type': u'c2'}]
    index = main
    sourcetype = tip:threats
    source = TIPTHREATS

    具体字段说明:
    ts:时间戳
    src:源ip+端口(可能没有，跟您配置有关)
    dest:查询目标
    intel_type:情报类型，可能有多个type,使用","分隔
    proto:网络请求协议，可能为空
    now:是一个数据，是TIP查询返回的具体内容
    index:索引名称
    sourcetype:源类型
    source:源


三、展示：
    当前页面只是展示了ioc命中的情况，您可以根据自身需要，配置更多的图和表。



