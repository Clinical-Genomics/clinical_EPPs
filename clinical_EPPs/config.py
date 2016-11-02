import ConfigParser
import os
import glob

clinical_eppsrc=glob.glob(os.path.expanduser('~/.clinical_eppsrc'))[0]
config = ConfigParser.SafeConfigParser()
config.readfp(open(clinical_eppsrc))

SQLALCHEMY_DATABASE_URI = config.get('demultiplex data', 'SQLALCHEMY_DATABASE_URI').rstrip()


