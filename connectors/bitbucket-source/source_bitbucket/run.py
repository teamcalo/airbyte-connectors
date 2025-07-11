#
# Copyright (c) 2024 Airbyte, Inc., all rights reserved.
#


import sys

from airbyte_cdk.entrypoint import launch
from source_bitbucket.source import SourceBitbucket

def run():
    source = SourceBitbucket()
    launch(source, sys.argv[1:])
