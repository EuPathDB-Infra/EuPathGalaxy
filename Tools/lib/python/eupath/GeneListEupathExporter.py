#!/usr/bin/python

from . import EupathExporterNew
from . import ReferenceGenome

class GeneListExporter(EupathExporterNew.Exporter):

    # Name given to this type of dataset and to the expected file
    GENE_LIST_TYPE = "GeneList"
    GENE_LIST_VERSION = "1.0"
    GENE_LIST_FILE = "genelist.txt"

    def initialize(self, stdArgsBundle, typeSpecificArgsList):

        super.initialize(self, stdArgsBundle, GeneListExport.GENE_LIST_TYPE, GeneListExport.GENE_LIST_VERSION)

        if len(typeSpecificArgsList) != 3:
            raise EupathExporterNew.ValidationException("The tool was passed an insufficient numbers of arguments.")

        # Override the dataset genome reference with that provided via the form.
        if len(typeSpecificArgsList[0].strip()) == 0:
            raise EupathExporterNew.ValidationException("A reference genome must be selected.")
        self._genome = ReferenceGenome.Genome(typeSpecificArgsList[0])
        self._dataset_file_path = typeSpecificArgsList[1]
        self._datatype = typeSpecificArgsList[2]

    def identify_dependencies(self):
        """
        The appropriate dependency(ies) will be determined by the reference genome selected - only one for now
        The EuPathDB reference genomes will have a project id, a EuPath release number, and a genome description
        all separated by a dash in the first instance and an underscore in the second instance.
        :return: list containing the single dependency with the component parts parsed out (only one for now)
        """
        return [{
            "resourceIdentifier": self._genome.identifier,
            "resourceVersion": self._genome.version,
            "resourceDisplayName": self._genome.display_name
        }]

    def identify_projects(self):
        """
        The appropriate project(s) will be determined by the reference genome selected - only one for now
        The project name must be listed in the SUPPORTED_PROJECTS array.  Failure to find it will be
        regarded as a validation exception.
        :return: list containing the single relevant EuPath project (only one for now)
        """
        return [self._genome.project]

    def identify_dataset_files(self):
        """
        The user provided gene list file is combined with the name EuPathDB expects
        for such a file
        :return: A list containing the single dataset file accompanied by its EuPathDB designation.
        """
        return [{"name": self.GENE_LIST_FILE, "path": self._dataset_file_path}]
