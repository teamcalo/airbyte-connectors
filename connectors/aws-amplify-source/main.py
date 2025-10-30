

import sys

from airbyte_cdk.entrypoint import launch
from source_aws_amplify import SourceAwsAmplify

if __name__ == "__main__":
    source = SourceAwsAmplify()
    launch(source, sys.argv[1:])
