
# start the runtime

# first build the runtime with all of the packages
#fab -f fabfile_builder.py -R d  build_runtime:runtime_configs/default_3.6.yaml


# save all the package runtime metadata
fab -f fabfile_builder.py -R d  get_metadata:/tmp/condaruntime,packages.json

# shrink the runtime
fab -f fabfile_builder.py -R d shrink_runtime

# perform the strip
fab -f fabfile_builder.py -R d backup_and_strip_sos:/tmp/condaruntime,/tmp/condaruntime.backup

# get the remap metadata
fab -f fabfile_builder.py -R d file_remap_dir:/tmp/conda,/tmp/condaruntime.backup

# create the tarfile
fab -f fabfile_builder.py -R d test_tar_runtime

# create the map json
fab -f fabfile_builder.py -R d test_deploy
