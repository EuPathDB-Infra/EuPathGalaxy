#!/usr/bin/python

import json
import tarfile
import time
import os
import shutil
import sys
import time
import requests
import tempfile
import contextlib
import re
import optparse
from urllib import request, parse
from urllib.error import HTTPError


# Superclass for all exporters
# POSTS data+metadata to the VDI service, and polls for response while status is till awaiting or in progress
# if dataset is invalid, fails, returning messages to user

# we always authenticate through the eupath dev gateway, even for prod, because it is needed for dev and ok for prod

def print_debug(msg):
    if os.getenv('DEBUG'):
        print(msg,  file=sys.stderr)

def get_ssl_verify():
    if os.getenv('NO_SSL_VER'):
        return False
    else:
        return True    
    
def execute(exporter):
    (options, args) = optparse.OptionParser().parse_args()
    stdArgsBundle = StandardArgsBundle(args)
    typeSpecificArgsList = stdArgsBundle.getTypeSpecificArgsList(args)
    exporter.initialize(stdArgsBundle, typeSpecificArgsList);

    try:
        print_debug("Attempting export.")
        exporter.export()
    except SystemException as ve:
        print(str(ve), file=sys.stderr)
        sys.exit(1)

# A small class capturing the standard args provided by galaxy        
class StandardArgsBundle:
    ARGS_LEN = 6

    def __init__(self, args):
        if len(args) < StandardArgsBundle.ARGS_LEN:
            raise SystemException("The export tool was passed an insufficient numbers of arguments.")
        self.dataset_name = args[0]
        self.summary = args[1]
        self.description = args[2]
        self.user_id = getWdkUserId(args[3])
        self.tool_directory = args[4] # Used to find the configuration file containing IRODS url and credentials
        self.output = args[5] # output file where we write a success message for the Galaxy user

    def getTypeSpecificArgsList(self, args):
        return args[StandardArgsBundle.ARGS_LEN : ]

# Abstract class to export to VEuPathDB.  Subclasses implement details for a given dataset type
class Exporter:
    POLLING_FACTOR = 1.5  # multiplier for progressive polling of status endpoint
    POLLING_INTERVAL_MAX = 60
    POLLING_TIMEOUT = 10 * POLLING_INTERVAL_MAX 
    SOURCE_GALAXY = "galaxy" # indicate to the service that Galaxy is the point of origin for this user dataset.

    def initialize(self, stdArgsBundle, dataset_type, dataset_version):
        self._stdArgsBundle = stdArgsBundle
        self._dataset_type = dataset_type
        self._dataset_version = dataset_version

        # read in config info
        (vdi_service_url, self._vdi_auth_token) = self.read_config()
        (vdi_service_url, self._vdi_auth_token, self._gateway_url, self._gateway_username, self._gateway_password) = self.read_config()

        self._vdi_datasets_url = vdi_service_url + "/vdi-datasets"

        gateway_cookie = self.get_eupath_gateway_cookie()

        self._headers = {"Accept": "application/json", "Admin-Token": self._vdi_auth_token, "User-ID": self._stdArgsBundle.user_id, "Cookie": gateway_cookie}

        # create a unique name for our tmp working dir and the tarball, of the form: 
        #   dataset_uNNNNNN_tTTTTTTT 
        # where NNNNNN is the VEupath user id and TTTTTT is the msec timestamp
        timestamp = int(time.time() * 1000)
        self._export_file_root = 'dataset_u' + str(self._stdArgsBundle.user_id) + '_t' + str(timestamp) + '_p' + str(os.getpid())
        print_debug("Export file root is " + self._export_file_root)


    def read_config(self):
        """
        Obtain the url and credentials to talk the the VDI service
        """
        config_path = self._stdArgsBundle.tool_directory + "/../../config/config.json"

        required_config = ["vdi-service-url", "vdi-auth-token", "gateway-url", "gateway-username", "gateway-password"]
        with open(config_path, "r") as config_file:
            config_json = json.load(config_file)
            missing_elements = set(required_config) - set(config_json.keys())
            if missing_elements:
                raise SystemException(f"The config file is missing: {missing_elements}")
            return (config_json["vdi-service-url"], config_json["vdi-auth-token"], config_json["gateway-url"], config_json["gateway-username"], config_json["gateway-password"])
                    
    def export(self):

        # Save the current working directory so we can get back to it
        orig_path = os.getcwd()

        with self.temporary_directory(self._export_file_root) as temp_path:
            os.chdir(temp_path)
            print_debug("temp path: " + temp_path)
            self.prepare_data_files(temp_path)
            tarball_name = self.create_tarball(temp_path)
            json_body = self.create_body_for_post()
            print_debug(json_body)
            user_dataset_id = self.post_metadata_and_data(json_body, tarball_name)
            print_debug("UD ID: " + user_dataset_id)
            self.poll_for_upload_complete(user_dataset_id)   # teriminates if system or validation error
            os.chdir(orig_path) # exit temp dir, prior to removing it
            print("Export complete. VEuPathDB User Dataset ID: " + user_dataset_id, file=sys.stdout)
            
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

    def prepare_data_files(self, temp_path):
        """
        Copies the user's dataset files to the datafiles folder of the temporary dir and changes each
        dataset filename conferred by Galaxy to a filename expected by VEuPathDB
        """
        for dataset_file in self.identify_dataset_files():
            clean_name = temp_path + "/" + self.clean_file_name(dataset_file['name'])
            print_debug("Creating dataset file: " + clean_name)
            shutil.copy(dataset_file['path'], clean_name)

    # replace undesired characters with underscore
    def clean_file_name(self, file_name):
        s = str(file_name).strip().replace(' ', '_')
        return re.sub(r'(?u)[^-\w.]', '_', s)
        
    def create_tarball(self, temp_path):
        """
        Package the tarball - contains the user's dataset files
        """
        tarball_name = self._export_file_root + ".tgz"
        with tarfile.open(tarball_name, "w:gz") as tarball:
            for filename in os.listdir(temp_path):
                print_debug("Adding file to tarball: " + filename)
                tarball.add(filename)
        #shutil.copy(tarball_name, "/home/galaxy/steve.tgz")
        return tarball_name       

    def get_eupath_gateway_cookie(
        params = {    
            "username": self._gateway_username,    
            "password": self._gateway_password,    
        }    
        query_string = parse.urlencode(params)    
        data = query_string.encode("utf-8")    

        req =  request.Request(self._login_server_url, data=data) # this will make the method "POST"
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        req.add_header("Content-Length", len(data))
        req.add_header("Cookie", "auth_probe=1")
        try:
            response = request.urlopen(req)
            cookie = response.info().get_all('Set-Cookie')
            # ['auth_tkt=Y2M2YzU1OTE5MTAzNGFjZDk0MjU5YjExMTBjZmFjOTM2NTk3MjhmZmFwaWRiIWFwaWRiITE3MDQ0MDUyNDc6; domain=veupathdb.org; path=/']
            auth_tkt = cookie[0].split("; ")[0].split("=")[1] 
            return auth_tkt
        except HTTPError as e:
            print("Exception authenticating through gateway. Code: " + str(e.code) + " " + e.reason, file=sys.stderr)
            print("Error URL: " + url, file=sys.stderr)            
            exit(1)

    def create_body_for_post(self):
        return {
            "name": self._stdArgsBundle.dataset_name,
            "summary": self._stdArgsBundle.summary,
            "dependencies": self.identify_dependencies(),
            "description": self._stdArgsBundle.description,
            "datasetType": {"name": self._dataset_type, "version": self._dataset_version},
            "projects": self.identify_projects(),
            "visibility": "private",
            "origin": self.SOURCE_GALAXY
        }

    def post_metadata_and_data(self, json_blob, tarball_name):
        print_debug("POSTING data.  Tarball name: " + tarball_name)
        try:
            url = self._vdi_datasets_url + "/admin/proxy-upload"
            form_fields = {"file": open(tarball_name, "rb"),  "meta":json.dumps(json_blob)}
            response = requests.post(url, files=form_fields, headers=self._headers, verify=get_ssl_verify())
            response.raise_for_status()
            print_debug(response.json())
            return response.json()['datasetID']
        except requests.exceptions.RequestException as e:
            self.handleRequestException(e, url, "Posting metadata and data to VDI")    

    def poll_for_upload_complete(self, user_dataset_id):
        start_time = time.time()
        poll_interval_seconds = 1
        while (self.check_upload_in_progress(user_dataset_id)):
            time.sleep(poll_interval_seconds)  # sleep for specified seconds
            if poll_interval_seconds < self.POLLING_INTERVAL_MAX:
                poll_interval_seconds *= self.POLLING_FACTOR
            if (time.time() - start_time > self.POLLING_TIMEOUT):
                raise SystemException("Timed out polling for upload completion status")

    # return True if still in progress; False if success.  Fail and terminate if system or validation error
    def check_upload_in_progress(self, user_dataset_id):
        print_debug("Polling for status")
        try:
            url = self._vdi_datasets_url + "/" + user_dataset_id
            response = requests.get(url, headers=self._headers, verify=get_ssl_verify())
            response.raise_for_status()
            json_blob = response.json()
            if json_blob["status"]["import"] == "complete":
                return False
            if json_blob["status"]["import"] == "invalid":
                self.handle_job_invalid_status(json_blob)
            return True  # status is awaiting or in progress
        except requests.exceptions.RequestException as e:
            self.handleRequestException(e, url, "Polling VDI for upload status")    


    def handleRequestException(self, e, url, msg):
        print("Error " + msg + ". Exception type: " + str(type(e)), file=sys.stderr)
        print("HTTP Code: " + str(e.response.status_code) + " " + e.response.text, file=sys.stderr)
        print("URL: " + url, file=sys.stderr)            
        exit(1)
        
    def handle_job_invalid_status(self, response_json):
        msgLines = ["Export failed.  Dataset had validation problems:"]
        for msg in response_json["importMessages"]:
            msgLines.append(msg)
        print('\n'.join(msgLines), file=sys.stderr)
        sys.exit(1)

    def printHttpErr(self, msg, status_code):
        print("Http Error (" + str(status_code) + "): " + msg, file=sys.stderr)            

    def output_success(self):
        header = "<html><body><h1>Good news!</h1><br />"
        msg = """
        <h2>Your export to VEuPathDB is complete<h2>.
         View the exported dataset by visiting the My Data Sets page in the appropriate VEuPathDB site
        <br />
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
        with open(self._stdArgsBundle.output, 'w') as file:
            file.write("%s%s" % (header,msg))

    def identify_projects(self):
        """
        An abstract method to be addressed by a specialized export tool that furnishes a VEuPathDB project list.
        :return: The project list to be returned should look as follows:
        [project1, project2, ... ]
        At least one valid VEuPathDB project must be listed
        """
        raise NotImplementedError(
            "The method 'identify_project(self)' needs to be implemented in the specialized export module.")

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


class SystemException(Exception):
    """
    An unexpected system error.
    """
    pass


class TransferException(Exception):
    """
    This represents the exception reported when the export of a dataset to the iRODS system returns a failure.
    """
    pass

# expect email of the form: sfischer.67546@veupathdb.org (where the number is the user ID)
def getWdkUserId(rawUserEmail):
    user_email = rawUserEmail.strip()
    # WDK user id is derived from the user email
    if not re.match(r'.+\.\d+@veupathdb.org$', user_email, flags=0):
        raise SystemException("The user email " + str(user_email) + " is not valid for the use of this tool.")
    galaxy_user = user_email.split("@")[0]
    return galaxy_user[galaxy_user.rfind(".") + 1:]

        
    
