from . import EupathExporter
from . import ReferenceGenome
import sys
import json
import os
import re

class RnaSeqExporter(EupathExporter.Exporter):

    """
INPUT
    tuple format is: [filepath, samplename, refgenome_key, suffix]

    suffixes are:  bw or txt (for fpkm files)
    
    type specific args:  
      strand param: 'stranded' or 'unstranded'
      for each sample, a list of tuple pairs, one txt tuple and one bw tuple: 
        - hopefully all tuples agree on ref genome
        - hopefully matching bw and txt files
        - if stranded, then sample has two pairs of tuples, one per strand
          - txt:
            - first tuple file name and sample name contain 'forward' in the name (sense)
            - second tuple file name and sample name contain 'reverse' in the name (antisense)
          - bw:
            - first tuple is strand one
            - second tuple is strand two

OUTPUT
  files given cannonical names:
     unstranded: sample.suffix (with sample name cleaned of icky characters)
     stranded:  
       -SAMPLE_NAME.forward.bw
       -SAMPLE_NAME.reverse.bw
       -SAMPLE_NAME.one.txt
       -SAMPLE_NAME.two.txt

  manifest.txt file with one line per file:
    for txt file:
      samplename filename strandinfo ('unstranded', 'sense' or 'antisense')
    for bw file:
      samplename filename strandinfo ('unstranded', 'strandone' or 'strandtwo')

  dependency info:
   - reference genome and version (unanimous consensus of the samples provided)
    """
    
    # Name given to this type of dataset and to the expected file
    TYPE = "RNASeq"
    VERSION = "1.0"

    def initialize(self, stdArgsBundle, typeSpecificArgsList):

        super().initialize(stdArgsBundle, RnaSeqExporter.TYPE, RnaSeqExporter.VERSION)

        if len(typeSpecificArgsList) < 5:
            raise EupathExporter.ValidationException("The tool was passed an insufficient numbers of arguments.")

        if (len(typeSpecificArgsList) - 1) % 4 != 0:
            raise EupathExporter.ValidationException("Invalid number of arguments.  Must be a strand followed by one or more 4-tuples.")

        strandednessParam = typeSpecificArgsList[0]
        if strandnessParam != "stranded" and strandnessParam != "unstranded":
            raise EupathExporter.ValidationException("Invalid strand param: " + strandednessParam)

        self._refGenome = ReferenceGenome.Genome(typeSpecificArgsList[3]) # grab ref genome from first tuple.  all others must agree

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
            rg = typeSpecificArgsList[i+2]
            suffix = typeSpecificArgsList[i+3]

            if rg.identifier != self._refGenome.identifier or rg.version != self._refGenome.version:
                raise EupathExporter.ValidationException("All datasets must have the same reference genome identifier and version")
            
            filename = self.clean_file_name(re.sub(r"\s+", "_", samplename) + "." + suffix)

            fileNumber += 1
            if strandednessParam == "stranded":
                if filename[-4:] == ".txt":
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
