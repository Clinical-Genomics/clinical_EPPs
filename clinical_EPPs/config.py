import configparser
import os
import glob

clinical_eppsrc=glob.glob(os.path.expanduser('~/.clinical_eppsrc'))[0]
config = configparser.ConfigParser()
config.readfp(open(clinical_eppsrc))

SQLALCHEMY_DATABASE_URI = config.get('demultiplex data', 'SQLALCHEMY_DATABASE_URI').rstrip()
CG_URL = config.get('CgFace', 'URL').rstrip()
