import EupathExporter
import ReferenceGenome
import sys
import os

class BigwigFilesExport(EupathExporter.Export):

    # Constants
    TYPE = "BigwigFiles"
    VERSION = "1.0"

    def __init__(self, args):
        EupathExporter.Export.__init__(self,
                                       BigwigFilesExport.TYPE,
                                       BigwigFilesExport.VERSION,
                                       None,
                                       args)

        # beyond the standard 7 params, this exporter requires one or more pairs of args: dataset1 dataset1.refGenome
        # dataset2...
        if len(args) < 10:
            raise EupathExporter.ValidationException("The tool was passed an insufficient numbers of arguments.")

        # list arguments (for debuging)
        # print >> sys.stderr, "args to BigwigFilesEupathExporter.py"
        # for i in range(0, len(args)):
        #     print >> sys.stderr, str(args[i])


        # grab first dataset provided ref genome
        self._initial_refGenome = args[9]

        self._datasetInfos = []
        
        # process variable number of [dataset refgenome] pairs.
        # confirm that all dataset provided ref genomes are identical.
        for i in range(7, len(args), 3):   # start on 8th arg, increment by 3

            # check file suffix (and set if needed)
            if args[i+1].endswith(".bigwig"):
                args[i+1] = args[i+1][0:-6] + "bw"
            elif not args[i+1].endswith(".bw"):
                args[i+1] = args[i+1] + ".bw"

            # check file size
            size = os.stat(args[i]).st_size
            sizeLimit = 500 * 1024 * 1024 # 500MB
            # print >> sys.stderr, "file size is " + str(size)
            if size > sizeLimit:
                raise EupathExporter.ValidationException("File exceeds 500MB size limit")

            if args[i+2] != self._initial_refGenome:
                raise EupathExporter.ValidationException("All provided bigwig datasets must have the same reference genome.  Found " + self._initial_refGenome + " and " + args[i+2])
            self._datasetInfos.append({"name": args[i+1], "path": args[i]})

        # for testing
        # sys.exit(1)

        # now override the dataset provided ref genome with the one obtained from the form assuming it is correctly
        # selected.  Otherwise throw an error.
        if len(args[6].strip()) == 0:
            raise EupathExporter.ValidationException("A reference genome must be selected.")
        self._refGenome = ReferenceGenome.Genome(args[6])


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
