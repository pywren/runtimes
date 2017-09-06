"""


mount -o size=100M -t tmpfs none /mnt/tmpfs

"""

import tarfile
from io import StringIO, BytesIO
import os
import numpy as np


def create_tarfile(filename, size_mb):
    tf = tarfile.open(filename, 'w')

    for i in range(size_mb):
        filename = "foo_{:03d}.data".format(i)
        size = 1000000
        data = (u"H"*size).encode('utf-8')
        tarinfo = tarfile.TarInfo(filename)

        tarinfo.size = len(data)
        string_obj = BytesIO(data)
        tf.addfile(tarinfo, fileobj=string_obj)





TARFILE_NAME = "/tmp/test.tar"
TARFILE_SIZE_MB = 110
DEST_PATH = "/mnt/tmpfs"
create_tarfile(TARFILE_NAME, TARFILE_SIZE_MB)
tf = tarfile.open(TARFILE_NAME, 'r')
try:
    tf.extractall(DEST_PATH)
except OSError as e:
    if e.args[0] == 28:
        print("NO SPACE ON DEVICE")
    
# truncate the tarfile 
tarfile_trunc = TARFILE_NAME + ".trunc"
fid = open(tarfile_trunc, 'wb')
fid.write(open(TARFILE_NAME, 'rb').read(100000))
fid.close()

tf = tarfile.open(tarfile_trunc, 'r')
try:
    tf.extractall("/tmp")
except tarfile.ReadError as e:
    print(e.args)


# turn tarfile into bad data
tarfile_bad = TARFILE_NAME + ".baddata"
fid = open(tarfile_bad, 'wb')
fid.write(np.random.bytes(1000000))
fid.close()
try:
    tf = tarfile.open(tarfile_bad, 'r')
    tf.extractall("/tmp")
except tarfile.ReadError as e:
    print(e.args)


