"""
Test script to run inside of runtime. Uses whatever version of pywren is installed
"""
import pywren 
import runtimes


for runtime_name, runtime_config in runtimes.RUNTIMES:
    python_ver = runtime_config[0]
        
    # create an executor
    config = pywren.wrenconfig.default()
    staged_runtime_url = runtimes.get_staged_runtime_key(runtime_name, python_ver)
    assert staged_runtime_url[:5] == "s3://"
    splits = staged_runtime_url[5:].split("/")
    bucket = splits[0]
    key = "/".join(splits[1:])
    config['runtime']['bucket'] = bucket
    config['runtime']['s3_key'] = key

    wrenexec = pywren.lambda_executor(config)
    
    def foo(x):
        return x + 1
    fut = wrenexec.call_async(foo, 2)
    assert fut.result() == 3

                          
