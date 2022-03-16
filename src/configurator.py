import yaml
from os.path import exists

class Configurator:

    config_file = "config.yml"
    config_folders = [ ".", "/data/config", "/config" ]
    ready = False
    config = None

    def __init__(self):
        for folder in self.config_folders:
            configpath = folder + "/" + self.config_file
            if exists(configpath):
                with open(configpath, "r") as stream:
                    try:
                        print("reading configuration: " + configpath)
                        self.config = yaml.safe_load(stream)
                        self.ready = True
                        return
                    except yaml.YAMLError as ex:
                        print("error parsing config file: " + str(ex))
        print("could not find valid configuration file")

    def is_ready(self):
        return self.ready

    def get(self, section, name):
        if section in self.config and self.config[section] is not None and name in self.config[section]:
            return self.config[section][name]
        else:
            return None
