from . import EupathExporter
from . import ReferenceGenome
import sys
import json
import os
import re

class RnaSeqExporter(EupathExporter.Exporter):

    """
INPUT
    type specific args:  
      strand param: 'stranded' or 'unstranded'
      a list of tuples. 

    tuple format is: [filepath, samplename, refgenome_key, suffix]

    suffixes provided by the galaxy UI are either 'bw' or 'txt' (for fpkm or tpm files)
    
OUTPUT
  files are given cannonical names:
     sample.suffix (with sample name cleaned of icky characters)
     for stranded, if txt file name contains forward or reverse, change to one or two

  manifest.txt file with one line per tuple:
    for txt file:
      samplename filename strandinfo ('unstranded', 'sense' or 'antisense')
    for bw file:
      samplename filename strandinfo ('unstranded', 'firststrand' or 'secondstrand')

  dependency info:
   - reference genome and version (unanimous consensus of the samples provided)

SEE VDI IMPORTER FOR VALIDATION RULES

    """
    
    # Name given to this type of dataset and to the expected file
    TYPE = "RNASeq"
    VERSION = "1.0"

    def initialize(self, stdArgsBundle, typeSpecificArgsList):

        super().initialize(stdArgsBundle, RnaSeqExporter.TYPE, RnaSeqExporter.VERSION)

        if len(typeSpecificArgsList) < 5:
            print("The tool was passed an insufficient numbers of arguments.", file=sys.stderr)
            exit(1)

        if (len(typeSpecificArgsList) - 1) % 4 != 0:
            print("Invalid number of arguments.  Must be stranded/unstranded followed by one or more 4-tuples.", file=sys.stderr)
            exit(1)

        strandednessParam = typeSpecificArgsList[0]
        if strandnessParam != "stranded" and strandnessParam != "unstranded":
            print("Invalid strand param: " + strandednessParam, file=sys.stderr)
            exit(1)

        # grab ref genome from first tuple.  all others must agree
        self._refGenomeKey = typeSpecificArgsList[3]
        self._refGenome = ReferenceGenome.Genome( self._refGenomeKey)

        self._datasetInfos = []

        # open manifest file for writing
        manifestPath = "/tmp/manifest." + str(os.getpid()) + ".txt"
        manifest = open(manifestPath, "w+")

        # process variable number of [filepath, samplename, refgenome_key, suffix] tubles
        fileNumber = 0
        for i in range(1, len(typeSpecificArgsList), 4):   # start after strand arg, increment by tuple size (4)
            
            # print >> sys.stderr, "args[" + str(i) + "] = " + args[i]
            path = typeSpecificArgsList[i+0]
            samplename = typeSpecificArgsList[i+1]
            refGenomeKey = typeSpecificArgsList[i+2]
            suffix = typeSpecificArgsList[i+3]

            if refGenomeKey != self._refGenomeKey
                print("All datasets must have the same reference genome identifier and version. Sample " + sampleName + " does not agree with the others: " + refGenomeKey, file=sys.stderr)
                exit(1)
            
            filename = self.clean_file_name(re.sub(r"\s+", "_", samplename) + "." + suffix)

            fileNumber += 1
            if strandednessParam == "stranded":
                if suffix == "txt":
                    filename = re.sub("forward", "one", re.sub("reverse", "two", filename))
                    samplename = re.sub("forward", "one", re.sub("reverse", "two", samplename))
                    strandedness = "sense" if (fileNumber % 2) == 1 else "antisense"
                else:
                    strandedness =  "firststrand" if (fileNumber % 2) == 1 else "secondstrand"
            else:
                strandedness = "unstranded"

            self._datasetInfos.append({"name": filename, "path": args[i]})
            print(samplename + "\t" + filename + "\t" + strandedness, file=manifest)

        manifest.close()
        self._datasetInfos.append({"name": "manifest.txt", "path": manifestPath})

        # print >> sys.stderr, "datasetInfos: " + json.dumps(self._datasetInfos) + "<<- END OF datasetInfos"

    def identify_dependencies(self):
        """
        The appropriate dependency(ies) will be determined by the reference genome selected - only one for now
        """
        return [{
            "resourceIdentifier": self._refGenome.identifier,
            "resourceVersion": self._refGenome.version,
            "resourceDisplayName": self._refGenome.display_name
        }]

    def identify_projects(self):
        return [self._refGenome.project]

    def identify_dataset_files(self):
        """
        :return: A list containing the dataset files accompanied by their VEuPathDB designation.
        """
        return self._datasetInfos
