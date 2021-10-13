from . import EupathExporter
from . import ReferenceGenome
import sys
import os
import subprocess


class VCFFileExport(EupathExporter.Export):

    # Constants
    TYPE = "VCFFile"
    VERSION = "1.0"

    def __init__(self, args):
        EupathExporter.Export.__init__(self,
                                       VCFFileExport.TYPE,
                                       VCFFileExport.VERSION,
                                       'validateVCF',
                                       args)

        self._datasetInfos = []

        # open manifest file
        manifestPath = "/tmp/manifest." + str(os.getpid()) + ".txt"
        manifest = open(manifestPath, "w+")

        for i in range(6, len(args), 2):
            print(i, args[i], file=sys.stdout)
            samplename = args[i+1]
            #filename = samplename + "." + args[i+2]
        ## Note in the xml this will need the right variables passed in - e.g. sample name, file format.
        

            self._datasetInfos.append({"name": samplename, "path": args[i]})
            print(samplename, file=manifest)
                

        self._datasetInfos.append({"name": "manifest.txt", "path": manifestPath})
        
        # Need this? 
        # self._refGenome = ReferenceGenome.Genome(args[10])


        # if len(args) < 10:
        #     raise EupathExporter.ValidationException("The tool was passed too few arguments.")

        
    def identify_dataset_files(self):
        """
        :return: A list containing the dataset files accompanied by their EuPathDB designation.
        """
        return self._datasetInfos


    def identify_projects(self):

        return [self._refGenome.project]
