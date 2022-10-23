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

# An abstract class to export to VEuPathDB.  Subclasses implement details for a given dataet type
class Exporter:
    SOURCE_GALAXY = "galaxy" # indicate to the service that Galaxy is the point of origin for this user dataset.

    def initialize(self, dataset_type, version, args):
        """
        Initializes the export class with the parameters needed to accomplish the export of user
        datasets on Galaxy to VEuPathDB projects.
        :param dataset_type: The VEuPathDB type of this dataset
        :param version: The version of the VEuPathDB type of this dataset
        :param args: An array of the input parameters
        """
        self._type = dataset_type
        self._version = version

        # Extract and transform the parameters as needed into member variables
        self.parse_params(args)

        # This is the name of the file to be exported sans extension.  It will be used to designate a unique temporary
        # directory and to export the tarball.
        # By convention, the dataset tarball is of the form dataset_uNNNNNN_tNNNNNNN.tgz where the NNNNNN following the _u
        # is the WDK user id and _t is the msec timestamp
        timestamp = int(time.time() * 1000)
        self._export_file_root = 'dataset_u' + str(self._user_id) + '_t' + str(timestamp) + '_p' + str(os.getpid())
        print("Export file root is " + self._export_file_root, file=sys.stdout)

        (self._url, self._user, self._pwd) = self.read_config()

    def parse_params(self, args):
        """
        Unpack generic parameters (the first 6).  The subclasses will handle the other parameters.
        """
        if len(args) < 6:
            raise ValidationException("The tool was passed an insufficient numbers of arguments.")
        self._dataset_name = args[0]
        self._summary = args[1]
        self._description = args[2]
        self._user_id = getWdkUserId(args[3])
        self._tool_directory = args[4] # Used to find the configuration file containing IRODS url and credentials
        self._output = args[5] # output file       

    def read_config(self):
        """
        Obtains the url and credentials and relevant collections needed to run the iRODS rest service.
        At some point, this information should be fished out of a configuration file.
        :return:  A tuple containing the url, user, and password, landing zone and flags collection,
         in that order
        """
        config_path = self._tool_directory + "/../../config/config.json"
        
        # The tool directory path seems glitchy on Globus Dev Galaxy instance after service restarts.
        # Uncomment to check.
        #print >> sys.stdout, "self._tool_directory is " + self._tool_directory
        with open(config_path, "r") as config_file:
            config_json = json.load(config_file)
            return (config_json["url"], config_json["user"], config_json["password"])
                    

    def export(self):

        # Save the current working directory so we can get back to it
        orig_path = os.getcwd()

        # Create a temporary directory in which to assemble the tarball.
        with self.temporary_directory(self._export_file_root) as temp_path:

            os.chdir(temp_path)
            self.package_data_files(temp_path)
            self.create_tarball()
            json_blob = self.create_json_for_post()
            dataset_id = self.post_json(json_blob)
            post_data(dataset_id, json_blob)
            os.chdir(orig_path) # exit temp dir, prior to removing it

    def create_body_for_post(self):
        return {
            "name": self._dataset_name,
            "summary": self._summary,
            "description": self._description
            "type": self._type,
            "projects": self.identify_projects(),
            "origin": SOURCE_GALAXY
        }


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
        return None;


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

        if self.identify_supported_projects() != None:
            for (project) in self.identify_projects():
                if project not in self.identify_supported_projects():
                    raise ValidationException("Sorry, you cannot export this kind of data to " + project)

        dataset_path = temp_path + "/" + self.DATASET_JSON
        with open(dataset_path, "w+") as json_file:
            json.dump({
              "type": {"name": self._type, "version": self._version},
              "projects": self.identify_projects(),
              "dataFiles": self.create_data_file_metadata(),
              "owner": self._user_id,
              "size": size,
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
            dataset_file_metadata = {}
            dataset_file_metadata["name"] = self.clean_file_name(dataset_file['name'])
            dataset_file_metadata["file"] = os.path.basename(dataset_file['path'])
            dataset_file_metadata["size"] = os.stat(dataset_file['path']).st_size
            dataset_files_metadata.append(dataset_file_metadata)
        return dataset_files_metadata

    
    # replace undesired characters with underscore
    def clean_file_name(self, file_name):
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
            for item in [self.DATAFILES]:
                tarball.add(item)

    def process_request(self, collection, source_file):
        """
        This method wraps the iRODS rest request into a try/catch to insure that bad responses are
        reflected back to the user.
        :param collection: the name of the workspaces collection to which the file is to be uploaded
        :param source_file: the name of the file to be uploaded to iRODS
        """
        rest_response = self.send_request(collection, source_file)
        try:
            rest_response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            print("Error: " + str(e), file=sys.stderr)
            sys.exit(1)

    def send_request(self, collection, source_file):
        """
        This request is intended as a multi-part form post containing one file to be uploaded.  iRODS Rest
        does an iput followed by an iget, apparently.  So the response can be used to insure proper
        delivery.
        :param collection: the name of the workspaces collection to which the file is to be uploaded
        :param source_file: the name of the file to be uploaded to iRODS
        :return: the http response from an iget of the uploaded file
        """
        request = self._url + collection + "/" + source_file
        headers = {"Accept": "application/json"}
        upload_file = {"uploadFile": open(source_file, "rb")}
        auth = HTTPBasicAuth(self._user, self._pwd)
        try:
            response = requests.post(request, auth=auth, headers=headers, files=upload_file)
            response.raise_for_status()
        except Exception as e:
            print("Error: The dataset export could not be completed at this time.  The VEuPathDB" \
                                 " workspace may be unavailable presently. " + str(e), file=sys.stderr)
            sys.exit(2)
        return response

    def get_flag(self, collection, source_file):
        """
        This method picks up any flag (success or failure) from the flags collection in iRODs related to the dataset
        exported to determine whether the export was successful.  If not, the nature of the failure is reported to the
        user.  The failure report will normally be very general unless the problem is one that can possibly be remedied
        by the user (e.g., going over quota).
        :param collection: The iRODS collection holding the status flags
        :param source_file: The dataset tarball name sans extension
        """
        time.sleep(5)  # arbitrary wait period before one time check for a flag.
        auth = HTTPBasicAuth(self._user, self._pwd)
        # Look for the presence of a success flag first and if none found, check for a failure flag.  If neither
        # found, assume that to be a failure also.
        try:
            request = self._url + collection + "/" + "success_" + source_file
            success = requests.get(request, auth=auth, timeout=5)
            if success.status_code == 404:
                request = self._url + collection + "/" + "failure_" + source_file
                failure = requests.get(request, auth=auth, timeout=5)
                if failure.status_code != 404:
                    raise TransferException(failure.content)
                else:
                    failure.raise_for_status()
            else:
                self.output_success()
                print("Your dataset has been successfully exported to VEuPathDB.", file=sys.stdout)
                print("Please visit an appropriate VEuPathDB site to view your dataset.", file=sys.stdout)
        except (requests.exceptions.ConnectionError, TransferException) as e:
            print("Error: " + str(e), file=sys.stderr)
            sys.exit(1)
        
    def connection_diagnostic(self):
        """
        Used to insure that the calling ip is the one expected (i.e., the one for which the
        firewall is opened).  In Globus Dev Galaxy instance calling the tool outside of Galaxy
        versus inside Galaxy resulted in different calling ip addresses.
        """
        request = "http://ifconfig.co"
        headers = {"Accept": "application/json"}
        try:
            response = requests.get(request, headers=headers)
            response.raise_for_status()
            print("Diagnostic Result: " + response.content, file=sys.stdout)
        except Exception as e:
            print("Diagnostic Error: " + str(e), file=sys.stderr)        

    @contextlib.contextmanager
    def temporary_directory(self, dir_name):
        """
        This method creates a temporary directory such that removal is assured once the
        program completes.
        :param dir_name: The name of the temporary directory
        :return: The full path to the temporary directory
        """
        temp_path = tempfile.mkdtemp(dir_name)
        try:
            yield temp_path
        finally:
            # Added the boolean arg because cannot remove top level of temp dir structure in
            # Globus Dev Galaxy instance and it will throw an Exception if the boolean, 'True', is not in place.
            shutil.rmtree(temp_path, True)

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
            file.write("%s%s" % (header,msg))



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

def getWdkUserId(rawUserEmail):
    user_email = rawUserEmail.strip()
    # WDK user id is derived from the user email
    if not re.match(r'.+\.\d+@veupathdb.org$', user_email, flags=0):
        raise ValidationException(
            "The user email " + str(user_email) + " is not valid for the use of this tool.")
    galaxy_user = user_email.split("@")[0]
    return galaxy_user[galaxy_user.rfind(".") + 1:]

import optparse
def execute(exporter):
    parser = optparse.OptionParser()
    (options, args) = parser.parse_args()
    exporter.initialize(args);

    #sys.tracebacklimit = 0

    try:
        print >> sys.stdout, "Try export."
        exporter.export()
    except EupathExporter.ValidationException as ve:
        print >> sys.stderr, str(ve)
        sys.exit(1)
