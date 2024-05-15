#!/usr/bin/env python3

import sys
#sys.path.insert(1, "/home/sfischer/sourceCode/EuPathGalaxy/Tools/lib/python/")
sys.path.insert(0, "/opt/galaxy/tools/eupath/Tools/lib/python")
from eupath import VcfFilesEupathExporter
from eupath import EupathExporter

def main():
    EupathExporter.execute(VcfFilesEupathExporter.VcfFilesExporter())

if __name__ == "__main__":
    sys.exit(main())
