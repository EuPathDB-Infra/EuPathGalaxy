#!/usr/bin/python

import json
import tarfile
import time
import os
import shutil
import sys
import requests
import tempfile
import contextlib
import re
from requests.auth import HTTPBasicAuth
from subprocess import Popen, PIPE


class Export:
    """
    This is a generic VEuPathDB export tool for Galaxy.  It is abstract and so must be subclassed by more
    specialized export tools that implement those abstract classes.
    """

    # Names for the 2 json files and the folder containing the dataset to be included in the tarball
    DATASET_JSON = "dataset.json"
    META_JSON = "meta.json"
    DATAFILES = "datafiles"

    def __init__(self, dataset_type, version, validation_script, args):
        """
        Initializes the export class with the parameters needed to accomplish the export of user
        datasets on Galaxy to VEuPathDB projects.
        :param dataset_type: The VEuPathDB type of this dataset
        :param version: The version of the VEuPathDB type of this dataset
        :param validation_script: A script that handles the validation of this dataset
        :param args: An array of the input parameters
        """
        self._type = dataset_type
        self._version = version
        self._validation_script = validation_script

        # Extract and transform the parameters as needed into member variables
        self.parse_params(args)

        # This msec timestamp is used to denote both the created and modified times.
        self._timestamp = int(time.time() * 1000)

        # This is the name of the file to be exported sans extension.  It will be used to designate a unique temporary
        # directory and to export both the tarball and the flag that triggers IRODS to process the tarball. By
        # convention, the dataset tarball is of the form dataset_uNNNNNN_tNNNNNNN.tgz where the NNNNNN following the _u
        # is the WDK user id and _t is the msec timestamp
        self._export_file_root = 'dataset_u' + str(self._user_id) + '_t' + str(self._timestamp) + '_p' + str(os.getpid())
        print >> sys.stdout, "Export file root is " + self._export_file_root

    def parse_params(self, args):
        """
        Salts away all generic parameters (i.e., the first 5 params) and do some initial validation.  The subclasses
        will handle the other parameters.
        :param args:
        :return:
        """
        if len(args) < 6:
            raise ValidationException("The tool was passed an insufficient numbers of arguments.")
        self._dataset_name = args[0]
        self._summary = args[1]
        self._description = args[2]

        # WDK user id is derived from the user email
        user_email = args[3].strip()
        if not re.match(r'.+\.\d+@veupathdb.org$', user_email, flags=0):
            raise ValidationException(
                "The user email " + str(user_email) + " is not valid for the use of this tool.")
        galaxy_user = user_email.split("@")[0]
        self._user_id = galaxy_user[galaxy_user.rfind(".") + 1:]

        # Used to find the configuration file containing IRODS url and credentials
        self._tool_directory = args[4]

        # Output file
        self._output = args[5]

    def validate_datasets(self):
        """
        Runs the validation script provided to the class upon initialization using the user's
        dataset files as standard input.
        :return:
        """

        if self._validation_script == None:
            return
        
        dataset_files = self.identify_dataset_files()

        validation_process = Popen(['python', self._tool_directory + "/../../bin/" + self._validation_script],
                                   stdin=PIPE, stdout=PIPE, stderr=PIPE)
        # output is a tuple containing (stdout, stderr)
        output = validation_process.communicate(json.dumps(dataset_files))
        if validation_process.returncode == 1:
            raise ValidationException(output[1])

    def identify_dependencies(self):
        """
        An abstract method to be addressed by a specialized export tool that furnishes a dependency json list.
        :return: The dependency json list to be returned should look as follows:
        [dependency1, dependency2, ... ]
        where each dependency is written as a json object as follows:
        {
          "resourceIdentifier": <value>,
          "resourceVersion": <value>,
          "resourceDisplayName": <value
        }
        Where no dependencies exist, an empty list is returned
        """
        raise NotImplementedError(
            "The method 'identify_dependencies(self)' needs to be implemented in the specialized export module.")

    def identify_projects(self):
        """
        An abstract method to be addressed by a specialized export tool that furnishes a VEuPathDB project list.
        :return: The project list to be returned should look as follows:
        [project1, project2, ... ]
        At least one valid VEuPathDB project must be listed
        """
        raise NotImplementedError(
            "The method 'identify_project(self)' needs to be implemented in the specialized export module.")

    def identify_supported_projects(self):
        """
        Override this method to provide a non-default list of projects.

        Default is None, interpreted as all projects are ok, ie, no constraints.
        """
        return None

    def identify_dataset_files(self):
        """
        An abstract method to be addressed by a specialized export tool that furnishes a json list
        containing the dataset data files and the VEuPathDB file names they must have in the tarball.
        :return: The dataset file list to be returned should look as follows:
        [dataset file1, dataset file2, ... ]
        where each dataset file is written as a json object as follows:
        {
          "name":<filename that VEuPathDB expects>,
          "path":<Galaxy path to the dataset file>
        At least one valid VEuPathDB dataset file must be listed
        """
        raise NotImplementedError(
            "The method 'identify_dataset_file(self)' needs to be implemented in the specialized export module.")

    def create_dataset_json_file(self, temp_path):
        """ Create and populate the dataset.json file that must be included in the tarball."""

        # Get the total size of the dataset files (needed for the json file)
        size = sum(os.stat(dataset_file['path']).st_size for dataset_file in self.identify_dataset_files())

        if self.identify_supported_projects() is not None:
            for (project) in self.identify_projects():
                if project not in self.identify_supported_projects():
                    raise ValidationException("Sorry, you cannot export this kind of data to " + project)

        dataset_path = temp_path + "/" + self.DATASET_JSON
        with open(dataset_path, "w+") as json_file:
            json.dump({
              "type": {"name": self._type, "version": self._version},
              "dependencies": self.identify_dependencies(),
              "projects": self.identify_projects(),
              "dataFiles": self.create_data_file_metadata(),
              "owner": self._user_id,
              "size": size,
              "created": self._timestamp
            }, json_file, indent=4)

    def create_metadata_json_file(self, temp_path):
        """" Create and populate the meta.json file that must be included in the tarball."""
        meta_path = temp_path + "/" + self.META_JSON
        with open(meta_path, "w+") as json_file:
            json.dump({"name": self._dataset_name,
                       "summary": self._summary,
                       "description": self._description
                       }, json_file, indent=4)

    def create_data_file_metadata(self):
        """
        Create a json object holding metadata for an array of dataset files.
        :return: json object to be inserted into dataset.json
        """
        dataset_files_metadata = []
        for dataset_file in self.identify_dataset_files():
            dataset_file_metadata = {"name": self.clean_file_name(dataset_file['name']),
                                     "file": os.path.basename(dataset_file['path']),
                                     "size": os.stat(dataset_file['path']).st_size}
            dataset_files_metadata.append(dataset_file_metadata)
        return dataset_files_metadata

    # replace undesired characters with underscore
    @staticmethod
    def clean_file_name(file_name):
        s = str(file_name).strip().replace(' ', '_')
        return re.sub(r'(?u)[^-\w.]', '_', s)
        
    def package_data_files(self, temp_path):
        """
        Copies the user's dataset files to the datafiles folder of the temporary dir and changes each
        dataset filename conferred by Galaxy to a filename expected by VEuPathDB
        """
        os.mkdir(temp_path + "/" + self.DATAFILES)
        for dataset_file in self.identify_dataset_files():
            shutil.copy(dataset_file['path'], temp_path + "/" + self.DATAFILES + "/" + self.clean_file_name(dataset_file['name']))

    def create_tarball(self):
        """
        Package the tarball - contains meta.json, dataset.json and a datafiles folder containing the
        user's dataset files
        """
        with tarfile.open(self._export_file_root + ".tgz", "w:gz") as tarball:
            for item in [self.META_JSON, self.DATASET_JSON, self.DATAFILES]:
                tarball.add(item)

    def export(self):
        """
        Does the work of exporting to VEuPathDB, a tarball consisting of the user's dataset files along
        with dataset and metadata json files.
        """

        # Apply the validation first.  If it fails, exit with a data error.
        self.validate_datasets()

        # We need to save the current working directory so we can get back to it when we are
        # finished working in our temporary directory.
        orig_path = os.getcwd()

        # We need to create a temporary directory in which to assemble the tarball.
        temp_path = "tmp"
        os.mkdir(temp_path)

        self.package_data_files(temp_path)
        self.create_metadata_json_file(temp_path)
        self.create_dataset_json_file(temp_path)

        os.chdir(temp_path)
        self.create_tarball()
        shutil.move(self._export_file_root + ".tgz", orig_path)
        os.chdir(orig_path)

    def output_success(self):
        header = "<html><body><h1>Good news!</h1><br />"
        msg = """
        <h2>Results of the VEuPathDB Export Tool<br />Bigwig Files to VEuPathDB</h2>
        <h3>Your set of bigwig files was exported from Galaxy to your account in VEuPathDB.
         For file access and to view in GBrowse, go to My Data Sets in the appropriate VEuPathDB site:
        </h3><br />
        Go to the appropriate VEuPathDB site (links below) to see it (and all your User Datasets):<br \>
        <a href='http://amoebadb.org/amoeba/app/workspace/datasets'>AmoebaDB</a><br />
        <a href='http://cryptodb.org/cryptodb/app/workspace/datasets'>CryptoDB</a><br />
        <a href='http://fungidb.org/fungidb/app/workspace/datasets'>FungiDB</a><br />
        <a href='http://giardiadb.org/giardiadb/app/workspace/datasets'>GiardiaDB</a><br />
        <a href='http://hostdb.org/hostdb/app/workspace/datasets'>HostDB</a><br />
        <a href='http://microsporidiadb.org/micro/app/workspace/datasets'>MicrosporidiaDB</a><br />
        <a href='http://piroplasmadb.org/piro/app/workspace/datasets'>PiroplasmaDB</a><br />
        <a href='http://plasmodb.org/plasmo/app/workspace/datasets'>PlasmoDB</a><br />
        <a href='http://schistodb.net/schisto/app/workspace/datasets'>SchistoDB</a><br />
        <a href='http://toxodb.org/toxo/app/workspace/datasets'>ToxoDB</a><br />
        <a href='http://trichdb.org/trichdb/app/workspace/datasets'>TrichDB</a><br />
        <a href='http://tritrypdb.org/tritrypdb/app/workspace/datasets'>TriTrypDB</a><br />
        </body></html>
        """
        with open(self._output, 'w') as file:
            file.write("%s%s" % (header, msg))


class ValidationException(Exception):
    """
    This represents the exception reported when a call to a validation script returns a data error.
    """
    pass


class TransferException(Exception):
    """
    This represents the exception reported when the export of a dataset to the iRODS system returns a failure.
    """
    pass
