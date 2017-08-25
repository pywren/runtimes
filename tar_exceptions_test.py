"""


mount -o size=100M -t tmpfs none /mnt/tmpfs

"""

import tarfile
from cStringIO import StringIO

TARFILE_NAME = "/tmp/test.tar.gz"

def create_tarifle(filename, size_mb)
    tf = tarfile.open(filename, 'w')

    for i in range(size_mb):
        filename = "foo_{:03d}.data".format(i)
        size = 1000000
        data = "H"*size
        tarinfo = tarfile.TarInfo(filename)

        tarinfo.size = len(data)

        tf.addfile(tarinfo, StringIO(data))


