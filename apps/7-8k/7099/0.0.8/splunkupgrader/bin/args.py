import shlex
from glob import glob
from tarfile import TarFile
import re

install_file = glob('splunk-*.tgz')[0]

tar = TarFile.open(install_file)
comp_files = tar.getnames()
tf = open("tf.txt", "w")
for file in comp_files:
    tf.write("{} \n".format(file))
tf.close()

