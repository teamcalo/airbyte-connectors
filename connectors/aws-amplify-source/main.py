#
# Copyright (c) 2024 Airbyte, Inc., all rights reserved.
#


import sys

from airbyte_cdk.entrypoint import launch
from source_aws_amplify import SourceAmplify

if __name__ == "__main__":
    source = SourceAmplify()
    launch(source, sys.argv[1:])
