from fabric.api import local, env, run, put, cd, task, sudo, settings, warn_only, lcd, path, get, execute, hide
import os

@task
def shrink_conda_clean(conda_install_dir):
    with path("{}/bin".format(conda_install_dir), behavior="prepend"):
        run("conda clean -y -i -t -p")

@task
def shrink_remove_pkg(conda_install_dir):
    run("rm -Rf {}/pkgs".format(conda_install_dir))

@task 
def shrink_remove_non_avx2_mkl(conda_install_dir):
    for g in ["*_mc.so", "*_mc2.so",  "*_mc3.so",  "*_avx512*", "*_avx.*"]:
        run('find {}/lib -name "{}" -delete'.format(conda_install_dir, g))


@task 
def shrink_strip_shared_libs(conda_install_dir):
    """
    Strip all shared libs (compiled with gcc) of debug information
    """
    run('find {} -name "*.so" -exec strip --strip-all  {{}} \;'.format(conda_install_dir))

@task
def shrink_delete_pyc(conda_install_dir):
    run('find {} -name "*.pyc" -delete'.format(conda_install_dir))

@task
def shrink_delete_static_libs(conda_install_dir):
    run('find {} -name "*.a" -delete'.format(conda_install_dir))


@task
def get_runtime_size(conda_install_dir):
    with hide():
        res = run('du -s {}'.format(conda_install_dir))
        print(res) 
        kb = int(res.split("\t")[0])
    return kb
