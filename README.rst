GNS3-ias
========

GNS3 Deadman Switch.

Linux/Unix
----------

Dependencies:

- Python version 3.3 or above
- pip & setuptools must be installed, please see http://pip.readthedocs.org/en/latest/installing.html
  (or sudo apt-get install python3-pip but install more packages)
- virtualenv was used during development
- virtualenv -p /usr/bin/python3.4 --distribute env (Remember to activate your virtualenv if used )
- sudo apt-get install libcurl4-gnutls-dev
- python-dateutil, to install pip install python-dateutil
- pycurl, to install pip install pycurl
- apache-libcloud
- requests

.. code:: bash

   cd gns3-dms
   sudo apt-get install python-virtualenv, python3-dev, libcurl4-gnutls-dev
   virtualenv -p /usr/bin/python3.4 --distribute env
   source ./env/bin/activate
   python setup.py install
   cd gns3dms
   gns3dms or gns3dms --help

