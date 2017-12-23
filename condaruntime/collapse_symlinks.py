import os
import glob2

def collapse_and_move_symlinks(root=".", dest="/tmp/conda_shared_objects/"):
    if not os.path.exists(dest):
        os.makedirs(dest)

    root = os.path.abspath(root)
    all_sos = glob2.glob(os.path.join(root, "**/*.so*"))
    for so in all_sos:
        if (not os.path.isfile(so)): continue
        base = os.path.basename(so)
        if (os.path.islink(so)):
            real = os.readlink(so)
            real = os.path.join(os.path.dirname(so), real)
            print("Removing {0}".format(so))
            os.remove(so)
            print("Unsymlinking {0} to {1}".format(real, so))
            os.rename(real, so)
        dest_so = os.path.join(dest, base)
        print(dest)
        print("Moving {0} to {1}".format(so, dest_so))
        os.rename(so, dest_so)

if __name__ == "__main__":
        collapse_and_move_symlinks()

