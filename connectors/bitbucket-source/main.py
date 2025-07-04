#
# Copyright (c) 2024 Airbyte, Inc., all rights reserved.
#


import sys

from airbyte_cdk.entrypoint import launch
from source_bitbucket import SourceBitbucket

if __name__ == "__main__":
    source = SourceBitbucket()
    launch(source, sys.argv[1:])
