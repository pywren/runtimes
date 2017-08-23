
# Overview

Building a runtime is complex for several reasons:

1. We need to build the runtime in an environment that mimics the
remote serverless environment as much as possible. This necessitates
a remote build process. 

2. As we've stated before, the anaconda runtime is large, and thus
we need to perform various manipulations to get it under 512 MB. 

3. We then need to get it into S3 and *shard* it so that N-thousand
lambda jobs can download it simultaneously. If we just upload
to a single object on S3, we will have simultaneous workers
bottlenecked by access. 

We currently use [Fabric](http://www.fabfile.org/ ) to orchestrate
this remote build process on a stand-alone EC2 instance. 

All runtimes are configured through a yaml file that looks 
like the following:

```
pythonver: '2.7'
miniconda_url: https://repo.continuum.io/miniconda/Miniconda2-latest-Linux-x86_64.sh
include:
  - minimal_2.7.yaml
conda:
    install:
      - numpy
      - numba
pip:
    install:
      - glob2
      - boto
    upgrade:
      - cloudpickle
      - enum34

extracmds:
  - "ls -lah"
```


# Getting started

First you need to launch the stand-alone machine that you will build
the runtime on. You must make sure that you have set the correct
amazon region and your EC2 key name in `builder_config.yaml`. 


```
fab -f fabfile_builder.py launch setup_ami
```

Then make sure you can ssh into the machine via:
```
fab -f fabfile_builder.py -R builder ssh
```

Then build your runtime using the config 
```
fab -f fabfile_builder.py -R builder build_runtime:your_config_filename.yaml
```

Then shrink the runtime
```
fab -f fabfile_builder.py -R builder shrink_runtime
```

Then deploy the runtime
```
fab -f fabfile_builder.py -R builder deploy_runtime:s3://your-bucket-name/runtime_name,your_config_filename.yaml
```

