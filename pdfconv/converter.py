# -*- coding: utf-8 -*-

######################################################################################
# 
#    Copyright (C) 2017 Mathias Markl
#
#    This program is free software; you can redistribute it and/or
#    modify it under the terms of the GNU General Public License
#    as published by the Free Software Foundation; either version 2
#    of the License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
#######################################################################################

import os
import io
import base64
import shutil
import urllib
import logging
import tempfile
import mimetypes
import subprocess

from contextlib import closing

logging.basicConfig(format= '%(asctime)s %(levelname)s - %(message)s', level=logging.INFO)

logger = logging.getLogger(__name__)

WD_FORMAT_PDF = 17
PP_FORMAT_PDF = 32
EX_FORMAT_PDF = 57

def convert_binary2pdf(binary, mimetype=None, filename=None, format="path"):
    """
    Converts a binary value to a PDF file.

    :param binary: The binary value
    :param mimetype: The mime tpye of the binary value
    :param filename: The filename of the binary value
    :param format: The output format (path, binary, file, base64 | default: path)
    :return: returns output depending on the given format
    """
    if not mimetype and not filename:
        raise ValueError("Either a mime type or a filename has to be given as argument.")
    else:
        if not mimetype:
            mimetype = mimetypes.guess_type(urllib.pathname2url(filename))[0]
        if not filename:
            extension =  mimetypes.guess_extension(mimetype)
        else:
            extension = os.path.splitext(filename)[1]
        tmp_wfile, tmp_wpath = tempfile.mkstemp(suffix=extension)
        tmp_pfile, tmp_ppath = tempfile.mkstemp(suffix=".pdf")
        if os.name == 'nt':
            tmp_wpath = tmp_wpath.replace("\\","\\\\")
            tmp_ppath = tmp_ppath.replace("\\","\\\\")
        with closing(os.fdopen(tmp_wfile, 'w')) as file:
            file.write(binary)
        (os.fdopen(tmp_pfile)).close()
        __dispatch[mimetype](tmp_wpath, tmp_ppath)
        os.remove(tmp_wpath)
        if format == 'path':
            return tmp_ppath
        else:
            try:
                with closing(open(tmp_ppath, 'rb')) as file:
                    if format == 'binary':
                        return file.read()
                    elif format == 'file':
                        output = io.BytesIO()
                        output.write(file.read())
                        output.close()
                        return output
                    elif format == 'base64':
                        return base64.b64encode(file.read())
                    else:
                        raise ValueError("Unknown format type. Use one of these: path, binary, file, base64")
            finally:
                os.remove(tmp_ppath)
        
def convert_document2pdf(input_path, output_path):
    """
    Converts a file to a PDF file.

    :param input_path: The input path
    :param output_path: The output path
    :return: returns nothing
    """
    if os.name == 'nt':
        try:
            _convert_word2pdf(input_path, output_path)
        except IOError as error:
            raise
        except (ImportError, WindowsError) as error:
            logger.info("Failed to use MS Office | %s | Fallback to unoconv" % error)
            _convert_unoconv2pdf(input_path, output_path)
    else:
        _convert_unoconv2pdf(input_path, output_path)

def convert_presentation2pdf(input_path, output_path):
    """
    Converts a file to a PDF file.

    :param input_path: The input path
    :param output_path: The output path
    :return: returns nothing
    """
    if os.name == 'nt':
        try:
            _convert_powerpoint2pdf(input_path, output_path)
        except IOError as error:
            raise
        except (ImportError, WindowsError) as error:
            logger.info("Failed to use MS Office | %s | Fallback to unoconv" % error)
            _convert_unoconv2pdf(input_path, output_path)
    else:
        _convert_unoconv2pdf(input_path, output_path)
                
def convert_spreadsheet2pdf(input_path, output_path):
    """
    Converts a file to a PDF file.

    :param input_path: The input path
    :param output_path: The output path
    :return: returns nothing
    """
    if os.name == 'nt':
        try:
            _convert_excel2pdf(input_path, output_path)
        except IOError as error:
            raise
        except (ImportError, WindowsError) as error:
            logger.info("Failed to use MS Office | %s | Fallback to unoconv" % error)
            _convert_unoconv2pdf(input_path, output_path)
    else:
        _convert_unoconv2pdf(input_path, output_path)
            
def _convert_word2pdf(input_path, output_path):
    try:
        import comtypes
        import comtypes.client
    except ImportError as error:
        raise 
    else:
        word = doc = None
        try:
            word = comtypes.client.CreateObject('Word.Application')
            doc = word.Documents.Open(input_path)
            doc.SaveAs(output_path, FileFormat=WD_FORMAT_PDF)
        except WindowsError as error:
            raise
        except comtypes.COMError as error:
            raise IOError(error)
        finally:
            doc and doc.Close()
            word and word.Quit()
            
def _convert_powerpoint2pdf(input_path, output_path):
    try:
        import comtypes
        import comtypes.client
    except ImportError as error:
        raise 
    else:
        powerpoint = slides = None
        try:
            powerpoint = comtypes.client.CreateObject('Powerpoint.Application')
            slides = powerpoint.Presentations.Open(input_path)
            slides.SaveAs(output_path, FileFormat=PP_FORMAT_PDF)
        except WindowsError as error:
            raise
        except comtypes.COMError as error:
            raise IOError(error)
        finally:
            slides and slides.Close()
            powerpoint and powerpoint.Quit()
            
def _convert_excel2pdf(input_path, output_path):
    try:
        import comtypes
        import comtypes.client
    except ImportError as error:
        raise 
    else:
        excel = wb = None
        try:
            excel = comtypes.client.CreateObject('Excel.Application')
            wb = excel.Workbooks.Open(input_path)
            wb.SaveAs(output_path, FileFormat=EX_FORMAT_PDF)
        except WindowsError as error:
            raise
        except comtypes.COMError as error:
            raise IOError(error)
        finally:
            wb and wb.Close()
            excel and excel.Quit()

def _convert_unoconv2pdf(input_path, output_path):
    try:
        p = subprocess.Popen(['unoconv', 'f pdf', '-o %s' % output_path, input_path], stdout=subprocess.PIPE)
        p.communicate()
        p.wait()
    except subprocess.CalledProcessError as error:
        raise
    except WindowsError as error:
        raise
    
__dispatch  = {
    'application/msword': convert_document2pdf,
    'application/ms-word': convert_document2pdf,
    'application/vnd.ms-word.document.macroEnabled.12': convert_document2pdf,
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': convert_document2pdf,
    'application/vnd.oasis.opendocument.text': convert_document2pdf,
    'application/mspowerpoint': _convert_powerpoint2pdf,
    'application/ms-powerpoint': _convert_powerpoint2pdf,
    'application/vnd.ms-powerpoint.addin.macroEnabled.12': _convert_powerpoint2pdf,
    'application/vnd.openxmlformats-officedocument.presentationml.presentation': _convert_powerpoint2pdf,
    'application/vnd.oasis.opendocument.presentation': _convert_powerpoint2pdf,
    'application/msexcel': _convert_excel2pdf,
    'application/ms-excel': _convert_excel2pdf,
    'application/vnd.ms-excel.sheet.macroEnabled.12': _convert_excel2pdf,
    'application/vnd.ms-excel.sheet.binary.macroEnabled.12': _convert_excel2pdf,
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': _convert_excel2pdf,
    'application/vnd.oasis.opendocument.spreadsheet': _convert_excel2pdf,
}