from . import EupathExporter
from . import ReferenceGenome
import os

class BigwigFilesExporter(EupathExporter.Export):
    """
INPUT
    type specific args:  
      - user's explicit choice of ref genome
      - one of more tuples of: [filepath, filename, refgenome_key]
        - error unless tuples agree on ref genome
        - all files must have .bw type

OUTPUT
  files given cannonical names:
     if file extension is .bw, no change
     if file extension is .bigwig, replace with .bw
     otherwise append .bw

  dependency info:
   - reference genome and version (as specified in dedicated ref genome parameter)
    """

    # Constants
    TYPE = "BigwigFiles"
    VERSION = "1.0"


    def initialize(self, stdArgsBundle, typeSpecificArgsList):

        super().initialize(stdArgsBundle, TYPE, VERSION)

        if len(typeSpecificArgsList) < 4:
            raise EupathExporter.ValidationException("The tool was passed an insufficient numbers of arguments.")

        if (len(typeSpecificArgsList) - 1) % 3 != 0:
            raise EupathExporter.ValidationException("Invalid number of arguments.  Must be a reference genome followed by one or more 3-tuples.")

        # Override the dataset genome reference with that provided via the form.
        if len(typeSpecificArgsList[0].strip()) == 0:
            raise EupathExporter.ValidationException("A reference genome must be selected.")
        self._refGenome = ReferenceGenome.Genome(typeSpecificArgsList[0])

        # list arguments (for debuging)
        # print >> sys.stderr, "args to BigwigFilesEupathExporter.py"
        # for i in range(0, len(args)):
        #     print >> sys.stderr, str(args[i])


        self._datasetInfos = []
        
        # process variable number of [dataset refgenome] pairs.
        # confirm that all dataset provided ref genomes are identical.
        for i in range(1, len(typeSpecificArgsList), 3):    # start after ref genome arg, increment by tuple size (3)

            path = typeSpecificArgsList[i+0]
            filename = typeSpecificArgsList[i+1]  # user's original file name
            rg = typeSpecificArgsList[i+2]

            # check file suffix (and set if needed)
            if filename.endswith(".bigwig"):
                filename = filename[0:-6] + "bw"
            elif not filename.endswith(".bw"):
                filename = filename + ".bw"

            # check file size
            size = os.stat(filename).st_size
            sizeLimit = 500 * 1024 * 1024 # 500MB
            # print >> sys.stderr, "file size is " + str(size)
            if size > sizeLimit:
                raise EupathExporter.ValidationException("File exceeds 500MB size limit: " + filename)

            if rg.identifier != self._refGenome.identifier or rg.version != self._refGenome.version:
                raise EupathExporter.ValidationException("File " + filename + " is annotated with ref genome " + rg.identifier + " version " + rg.version " which conflicts with " + self._refGenome.identifier + " " + self._refGenome.version)

            self._datasetInfos.append({"name": filename, "path": path})

        # for testing
        # sys.exit(1)

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
