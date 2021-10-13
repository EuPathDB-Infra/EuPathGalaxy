#!/usr/bin/python

from . import EupathExporter
import biom
from biom.cli.table_validator import _validate_table
from biom.parse import load_table
class BiomExport(EupathExporter.Export):

    BIOM_TYPE = "BIOM"
    BIOM_VERSION = "1.0, 2.0, or 2.1"

    def __init__(self, args):
        """
        Initializes the gene list export class with the parameters needed to accomplish the particular
        type of export.
        :param args: parameters provided from tool form
        """
        EupathExporter.Export.__init__(self,
                                       BiomExport.BIOM_TYPE,
                                       BiomExport.BIOM_VERSION,
                                       None,
                                       args)

        # generic 7 arguments and then dataset file path
        if len(args) < 8:
            raise EupathExporter.ValidationException("The tool was passed an insufficient numbers of arguments:", args)

        self._dataset_file_path = args[7]


    def validate_datasets(self):
        # try read a file
# gives stupid errors like "Invalid format 'Biological Observation Matrix 0.9.1-dev', must be '1.0.0'"
#        valid, report = _validate_table(self._dataset_file_path)
#        if not valid:
#          raise EupathExporter.ValidationException(report)
        try:        
          table=load_table(self._dataset_file_path)
        except ValueError, e:
            raise EupathExporter.ValidationException("Could not load the file as BIOM - does it conform to the specification on https://biom-format.org?", e)

        give_table_extra_methods(table)
        generated_by="MicrobiomeDb exporter"

        with open(self._dataset_file_path+".metadata.json", 'w') as f1:
          table.to_json_but_only_metadata(generated_by, direct_io=f1)

        with open(self._dataset_file_path+".data.tsv", 'w') as f2:
          table.to_json_but_only_data_and_not_json_but_tsv(generated_by, direct_io=f2)
          
    def identify_dependencies(self):
        return []

    def identify_projects(self):
        return ["MicrobiomeDB"]

    def identify_supported_projects(self):
        return ["MicrobiomeDB"]

    def identify_dataset_files(self):
        return [
          {"name": "uploaded.biom", "path": self._dataset_file_path},
          {"name": "metadata.json", "path": self._dataset_file_path+".metadata.json"},
          {"name": "data.tsv", "path": self._dataset_file_path + ".data.tsv"}
        ]

    def output_success(self):
        header = "<html><body><h1>Good news!</h1><br />"
        msg = """
        <h2>Results of the VEuPathDB Export Tool<br />BIOM files to MicrobiomeDB</h2>
        <h3>Your BIOM file was exported from Galaxy to your account in VEuPathDB.
         For file access, go to the My Data Sets section on MicrobiomeDB:
          <a href='http://microbiomedb.org/mbio/app/workspace/datasets'>My Data Sets</a><br />
        </h3><br />
        </body></html>
        """
        with open(self._output, 'w') as file:
            file.write("%s%s" % (header,msg))



def give_table_extra_methods(table):
# just my looking at the name you know this is gonna be good isn't it
# takes a table and attaches these two methods to it:
# - to_json_but_only_metadata
# - to_json_but_only_data_and_not_json_but_tsv
#
# Done by twice replicating the 200 lines long method from
# https://github.com/biocore/biom-format/blob/fd84172794d14a741a5764234d7a28416b9dba08/biom/table.py#L4451
# and judiciously commenting stuff out
# 
# View in python-coloring editor to see what got commented out or diff with the package code to find out how they were changed
# Scroll to the bottom of the file to see how they get added
#

#
#   Here are the globals
#
    from future.utils import string_types
    def get_biom_format_version_string(version=None):
        """Returns the current Biom file format version.
        Parameters
        ----------
        version : tuple
            a tuple containing the version number of the biom table
        """
        if version is None:
            return "Biological Observation Matrix 1.0.0"
        else:
            return "Biological Observation Matrix %s.%s.0" % (version[0],
                                                              version[1])

    def get_biom_format_url_string():
        return "http://biom-format.org"

    from datetime import datetime
    from json import dumps

    def to_json_but_only_metadata(self, generated_by, direct_io=None):
        """Returns a JSON string representing the table in BIOM format.
        Parameters
        ----------
        generated_by : str
            a string describing the software used to build the table
        direct_io : file or file-like object, optional
            Defaults to ``None``. Must implementing a ``write`` function. If
            `direct_io` is not ``None``, the final output is written directly
            to `direct_io` during processing.
        Returns
        -------
        str
            A JSON-formatted string representing the biom table
        """
        if not isinstance(generated_by, string_types):
            raise TableException("Must specify a generated_by string")

        # Fill in top-level metadata.
        if direct_io:
            direct_io.write(u'{')
            direct_io.write(u'"id": "%s",' % str(self.table_id))
            direct_io.write(
                u'"format": "%s",' %
                get_biom_format_version_string((1, 0)))  # JSON table -> 1.0.0
            direct_io.write(
                u'"format_url": "%s",' %
                get_biom_format_url_string())
            direct_io.write(u'"generated_by": "%s",' % generated_by)
            direct_io.write(u'"date": "%s",' % datetime.now().isoformat())
        else:
            id_ = u'"id": "%s",' % str(self.table_id)
            format_ = u'"format": "%s",' % get_biom_format_version_string(
                (1, 0))  # JSON table -> 1.0.0
            format_url = u'"format_url": "%s",' % get_biom_format_url_string()
            generated_by = u'"generated_by": "%s",' % generated_by
            date = u'"date": "%s",' % datetime.now().isoformat()

        # Determine if we have any data in the matrix, and what the shape of
        # the matrix is.
        try:
            num_rows, num_cols = self.shape
        except:  # noqa
            num_rows = num_cols = 0
        has_data = True if num_rows > 0 and num_cols > 0 else False

        # Default the matrix element type to test to be an integer in case we
        # don't have any data in the matrix to test.
        test_element = 0
        if has_data:
            test_element = self[0, 0]

        # Determine the type of elements the matrix is storing.
        if isinstance(test_element, int):
            matrix_element_type = u"int"
        elif isinstance(test_element, float):
            matrix_element_type = u"float"
        elif isinstance(test_element, string_types):
            matrix_element_type = u"str"
        else:
            raise TableException("Unsupported matrix data type.")

        # Fill in details about the matrix.
        if direct_io:
            direct_io.write(
                u'"matrix_element_type": "%s",' %
                matrix_element_type)
            direct_io.write(u'"shape": [%d, %d],' % (num_rows, num_cols))
        else:
            matrix_element_type = u'"matrix_element_type": "%s",' % \
                matrix_element_type
            shape = u'"shape": [%d, %d],' % (num_rows, num_cols)

        # Fill in the table type
        if self.type is None:
            type_ = u'"type": null,'
        else:
            type_ = u'"type": "%s",' % self.type

        if direct_io:
            direct_io.write(type_)
        # Fill in details about the rows in the table and fill in the matrix's
        # data. BIOM 2.0+ is now only sparse
        if direct_io:
            direct_io.write(u'"matrix_type": "sparse",')
            """
            direct_io.write(u'"data": [')
            """
        else:
            matrix_type = u'"matrix_type": "sparse",'
            """
            data = [u'"data": [']
            """
            data=[]
        max_row_idx = len(self.ids(axis='observation')) - 1
        max_col_idx = len(self.ids()) - 1
        rows = [u'"rows": [']
        have_written = False
        for obs_index, obs in enumerate(self.iter(axis='observation')):
            # i'm crying on the inside
            if obs_index != max_row_idx:
                rows.append(u'{"id": %s, "metadata": %s},' % (dumps(obs[1]),
                                                              dumps(obs[2])))
            else:
                rows.append(u'{"id": %s, "metadata": %s}],' % (dumps(obs[1]),
                                                               dumps(obs[2])))

            # turns out its a pain to figure out when to place commas. the
            # simple work around, at the expense of a little memory
            # (bound by the number of samples) is to build of what will be
            # written, and then add in the commas where necessary.
            built_row = []
            for col_index, val in enumerate(obs[0]):
                if float(val) != 0.0:
                    built_row.append(u"[%d,%d,%r]" % (obs_index, col_index,
                                                      val))
            """
            if built_row:
                # if we have written a row already, its safe to add a comma
                if have_written:
                    if direct_io:
                        direct_io.write(u',')
                    else:
                        data.append(u',')
                if direct_io:
                    direct_io.write(u','.join(built_row))
                else:
                    data.append(u','.join(built_row))

                have_written = True
            """
        """
        # finalize the data block
        if direct_io:
            direct_io.write(u"],")
        else:
            data.append(u"],")
        """
        # Fill in details about the columns in the table.
        columns = [u'"columns": [']
        for samp_index, samp in enumerate(self.iter()):
            if samp_index != max_col_idx:
                columns.append(u'{"id": %s, "metadata": %s},' % (
                    dumps(samp[1]), dumps(samp[2])))
            else:
                columns.append(u'{"id": %s, "metadata": %s}]' % (
                    dumps(samp[1]), dumps(samp[2])))

        if rows[0] == u'"rows": [' and len(rows) == 1:
            # empty table case
            rows = [u'"rows": [],']
            columns = [u'"columns": []']

        rows = u''.join(rows)
        columns = u''.join(columns)

        if direct_io:
            direct_io.write(rows)
            direct_io.write(columns)
            direct_io.write(u'}')
        else:
            return u"{%s}" % ''.join([id_, format_, format_url, matrix_type,
                                      generated_by, date, type_,
                                      matrix_element_type, shape,
                                      u''.join(data), rows, columns])

# This is also copy pasted from
# https://github.com/biocore/biom-format/blob/fd84172794d14a741a5764234d7a28416b9dba08/biom/table.py#L4451

    def to_json_but_only_data_and_not_json_but_tsv(self, generated_by, direct_io=None):
        """Returns a JSON string representing the table in BIOM format.
        Parameters
        ----------
        generated_by : str
            a string describing the software used to build the table
        direct_io : file or file-like object, optional
            Defaults to ``None``. Must implementing a ``write`` function. If
            `direct_io` is not ``None``, the final output is written directly
            to `direct_io` during processing.
        Returns
        -------
        str
            A JSON-formatted string representing the biom table
        """
        """
        if not isinstance(generated_by, string_types):
            raise TableException("Must specify a generated_by string")
        # Fill in top-level metadata.
        if direct_io:
            direct_io.write(u'{')
            direct_io.write(u'"id": "%s",' % str(self.table_id))
            direct_io.write(
                u'"format": "%s",' %
                get_biom_format_version_string((1, 0)))  # JSON table -> 1.0.0
            direct_io.write(
                u'"format_url": "%s",' %
                get_biom_format_url_string())
            direct_io.write(u'"generated_by": "%s",' % generated_by)
            direct_io.write(u'"date": "%s",' % datetime.now().isoformat())
        else:
            id_ = u'"id": "%s",' % str(self.table_id)
            format_ = u'"format": "%s",' % get_biom_format_version_string(
                (1, 0))  # JSON table -> 1.0.0
            format_url = u'"format_url": "%s",' % get_biom_format_url_string()
            generated_by = u'"generated_by": "%s",' % generated_by
            date = u'"date": "%s",' % datetime.now().isoformat()

        # Determine if we have any data in the matrix, and what the shape of
        # the matrix is.
        try:
            num_rows, num_cols = self.shape
        except:  # noqa
            num_rows = num_cols = 0
        has_data = True if num_rows > 0 and num_cols > 0 else False

        # Default the matrix element type to test to be an integer in case we
        # don't have any data in the matrix to test.
        test_element = 0
        if has_data:
            test_element = self[0, 0]

        # Determine the type of elements the matrix is storing.
        if isinstance(test_element, int):
            matrix_element_type = u"int"
        elif isinstance(test_element, float):
            matrix_element_type = u"float"
        elif isinstance(test_element, string_types):
            matrix_element_type = u"str"
        else:
            raise TableException("Unsupported matrix data type.")

        # Fill in details about the matrix.
        if direct_io:
            direct_io.write(
                u'"matrix_element_type": "%s",' %
                matrix_element_type)
            direct_io.write(u'"shape": [%d, %d],' % (num_rows, num_cols))
        else:
            matrix_element_type = u'"matrix_element_type": "%s",' % \
                matrix_element_type
            shape = u'"shape": [%d, %d],' % (num_rows, num_cols)

        # Fill in the table type
        if self.type is None:
            type_ = u'"type": null,'
        else:
            type_ = u'"type": "%s",' % self.type

        if direct_io:
            direct_io.write(type_)

        # Fill in details about the rows in the table and fill in the matrix's
        # data. BIOM 2.0+ is now only sparse
        if direct_io:
            direct_io.write(u'"matrix_type": "sparse",')
            direct_io.write(u'"data": [')
        else:
            matrix_type = u'"matrix_type": "sparse",'
            data = [u'"data": [']

        max_row_idx = len(self.ids(axis='observation')) - 1
        max_col_idx = len(self.ids()) - 1
        rows = [u'"rows": [']
        have_written = False
        """
        for obs_index, obs in enumerate(self.iter(axis='observation')):
            """
            # i'm crying on the inside
            if obs_index != max_row_idx:
                rows.append(u'{"id": %s, "metadata": %s},' % (dumps(obs[1]),
                                                              dumps(obs[2])))
            else:
                rows.append(u'{"id": %s, "metadata": %s}],' % (dumps(obs[1]),
                                                               dumps(obs[2])))

            # turns out its a pain to figure out when to place commas. the
            # simple work around, at the expense of a little memory
            # (bound by the number of samples) is to build of what will be
            # written, and then add in the commas where necessary.
            built_row = []
            """
            for col_index, val in enumerate(obs[0]):
                if float(val) != 0.0:
                    if direct_io:
                        direct_io.write(u"%d\t%d\t%r\n" % (obs_index, col_index,
                                                      val))
                    else:
                        data.append([obs_index, col_index, val])
            """
                    built_row.append(u"[%d,%d,%r]" % (obs_index, col_index,
                                                      val))
            if built_row:
                # if we have written a row already, its safe to add a comma
                if have_written:
                    if direct_io:
                        direct_io.write(u',')
                    else:
                        data.append(u',')
                if direct_io:
                    direct_io.write(u','.join(built_row))
                else:
                    data.append(u','.join(built_row))

                have_written = True
            """
        """
        # finalize the data block
        if direct_io:
            direct_io.write(u"],")
        else:
            data.append(u"],")

        # Fill in details about the columns in the table.
        columns = [u'"columns": [']
        for samp_index, samp in enumerate(self.iter()):
            if samp_index != max_col_idx:
                columns.append(u'{"id": %s, "metadata": %s},' % (
                    dumps(samp[1]), dumps(samp[2])))
            else:
                columns.append(u'{"id": %s, "metadata": %s}]' % (
                    dumps(samp[1]), dumps(samp[2])))

        if rows[0] == u'"rows": [' and len(rows) == 1:
            # empty table case
            rows = [u'"rows": [],']
            columns = [u'"columns": []']

        rows = u''.join(rows)
        columns = u''.join(columns)

        if direct_io:
            direct_io.write(rows)
            direct_io.write(columns)
            direct_io.write(u'}')
        else:
            return u"{%s}" % ''.join([id_, format_, format_url, matrix_type,
                                      generated_by, date, type_,
                                      matrix_element_type, shape,
                                      u''.join(data), rows, columns])
        """
#
#
# Here's the patching
# Taken from https://stackoverflow.com/a/28060251
#
#
    table.to_json_but_only_metadata = to_json_but_only_metadata.__get__(table)
    table.to_json_but_only_data_and_not_json_but_tsv = to_json_but_only_data_and_not_json_but_tsv.__get__(table)
