import EupathExporter
import ReferenceGenome


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

        # beyond the standard 6 params, this exporter requires one or more pairs of args: dataset1 dataset1.refGenome
        # dataset2...
        if len(args) < 9:
            raise EupathExporter.ValidationException("The tool was passed an insufficient numbers of arguments.")

        # grab first provided ref genome, as the master
        self._refGenome = ReferenceGenome.Genome(args[8])
        self._datasetInfos = []
        
        # process variable number of [dataset refgenome] pairs.
        # confirm that all regenomes are identical.
        for i in range(6, len(args), 3):   # start on 7th arg, increment by 2
            #if not args[i+1].endswith(".bigwig") and not args[i+1].endswith(".bw"):
            #    raise EupathExporter.ValidationException("All datafiles must have either the .bigwig or .bw extension.")
            if args[i+2] != self._refGenome.identifier:
                raise EupathExporter.ValidationException("All provided bigwig datasets must have the same reference genome.")
            self._datasetInfos.append({"name": args[i+1], "path": args[i]})

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
        :return: A list containing the dataset files accompanied by their EuPathDB designation.
        """
        return self._datasetInfos
