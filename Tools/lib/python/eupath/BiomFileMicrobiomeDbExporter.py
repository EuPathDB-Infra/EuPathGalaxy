#!/usr/bin/python

import EupathExporter

class BiomExport(EupathExporter.Export):

    BIOM_TYPE = "BIOM"
    BIOM_VERSION = "1.0"
    BIOM_FILE = "data.biom"

    BIOM_VALIDATION_SCRIPT = "validateBiom"

    def __init__(self, args):
        """
        Initializes the gene list export class with the parameters needed to accomplish the particular
        type of export.
        :param args: parameters provided from tool form
        """
        EupathExporter.Export.__init__(self,
                                       BiomExport.BIOM_TYPE,
                                       BiomExport.BIOM_VERSION,
                                       BiomExport.BIOM_VALIDATION_SCRIPT,
                                       args)

        # generic 7 arguments and then dataset file path
        if len(args) < 8:
            raise EupathExporter.ValidationException("The tool was passed an insufficient numbers of arguments.")

        self._dataset_file_path = args[7]

    def identify_dependencies(self):
        return []

    def identify_projects(self):
        return ["MicrobiomeDB"]

    def identify_supported_projects(self):
        return ["MicrobiomeDB"]

    def identify_dataset_files(self):
        """
        The user provided gene list file is combined with the name EuPathDB expects
        for such a file
        :return: A list containing the single dataset file accompanied by its EuPathDB designation.
        """
        return [{"name": self.BIOM_FILE, "path": self._dataset_file_path}]

    def output_success(self):
        header = "<html><body><h1>Good news!</h1><br />"
        msg = """
        <h2>Results of the EuPathDB Export Tool<br />BIOM files to MicrobiomeDB</h2>
        <h3>Your BIOM file was exported from Galaxy to your account in EuPathDB.
         For file access, go to My Data Sets section
          <a href='http://microbiomedb.org/mbio/app/workspace/datasets'>My Data Sets section</a><br />
         on MicrobiomeDB.
        </h3><br />
        </body></html>
        """
        with open(self._output, 'w') as file:
            file.write("%s%s" % (header,msg))


