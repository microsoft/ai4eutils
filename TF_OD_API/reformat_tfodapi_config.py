# Simple script for reformatting a pipeline configuration in a 
# canonical format such that it is possible to use diff to compare
# two pipelines

# You can directly compare two files using:
#   diff <(python reformat.py pipeline1.config) <(python reformat.py pipeline2.config)

# Remember to put the models/research directory in your PYTHONPATH before calling
# the script

from object_detection.protos import pipeline_pb2
import google.protobuf.text_format as txtf
import sys

pipeline = pipeline_pb2.TrainEvalPipelineConfig()
with open(sys.argv[1]) as f:
    txtf.Merge(f.read(), pipeline)
print(pipeline)
