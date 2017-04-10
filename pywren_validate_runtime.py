import pywren
import sys

s3_bucket = sys.argv[1]
s3_key = sys.argv[2]

def test_function(x):
    return x + 1


pywren_config = pywren.wrenconfig.default()
pywren_config['runtime']['s3_bucket'] = s3_bucket
pywren_config['runtime']['s3_key'] = s3_key
wrenexec = pywren.lambda_executor(pywren_config)

fut = wrenexec.call_async(test_function, 10)
# FIXME make this test more

assert(fut.result() == 11)
