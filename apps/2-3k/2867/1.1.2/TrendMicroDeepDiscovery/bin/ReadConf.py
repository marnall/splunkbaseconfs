import ConfigParser

class ReadConf:
    def __init__(self, filepath, ACSection):
        self.filepath = filepath
        self.ACSection = ACSection
        self.Config = ConfigParser.ConfigParser()
        self.Config.read(self.filepath)
        self.ackey = self.Config.get(self.ACSection[0],'activation_key')
        self.expired_date = self.Config.get(self.ACSection[0],'expired_date')
        self.grace_period = self.Config.get(self.ACSection[0],'grace_period')
        self.host = self.Config.get(self.ACSection[1],'host')
        self.port = self.Config.get(self.ACSection[1],'port')

    def setACConf(self, json_result):
        self.ackey = json_result['ackey']
        self.expired_date = json_result['expired']
        self.grace_period = json_result['grace']
        self.Config.set(self.ACSection[0],'activation_key', json_result['ackey'])
        self.Config.set(self.ACSection[0],'expired_date', json_result['expired'])
        self.Config.set(self.ACSection[0],'grace_period', json_result['grace'])

        with open(self.filepath, 'wb') as configfile:
            self.Config.write(configfile)
