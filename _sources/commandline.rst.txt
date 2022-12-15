Command line tools
==================

There are two different command line tools. One is used to help configuring the system in various ways from creating keys to testing out
if a specific filter is behaving as expected. The other tool is for communicating with the server.

-----------------------
baltrad-exchange-config
-----------------------

Like the command indicates, it's used for various configuration purposes. Most essential is the one for creating keys since it's essential
for a running system.

create_keys
___________
This command will give you help creating the public/private keys used for the signature handling within the system. The default behaviour is to use "crypto" which
is the internally created handling using PyCryptodome as library and the service currently supports RSA and DSA keys. The nodename is essential since it will
be used to set information that will be used when identifying this node to other nodes. The command in itself is straight forward

You will get help on how to use the command by using the option '--help'

.. code:: sh

   %> baltrad-exchange-config create_keys --help

   Options:
  -h, --help            show this help message and exit
  -v, --verbose         be verbose
  --type=TYPE           Library to use for generating key-pair to create.
                        Default: crypto (which is the internal key handling).
                        Other libraries can be keyczar
  --encryption=ENCRYPTION
                        Encryption method to use. For internal use you can
                        either choose dsa or rsa. Default is: dsa
  --destination=DESTINATION
                        Directory where the keys should be placed. Default is
                        current directory.
  --nodename=NODENAME   Name of the node for this server.

  

.. code:: sh

   %> baltrad-exchange-config create_keys --type=crypto --encryption=dsa --destination=/etc/baltrad/exchange/crypto-keys --nodename=myserver
   Created: 
     Private key: /etc/baltrad/exchange/crypto-keys/myserver.private
     Public  key: /etc/baltrad/exchange/crypto-keys/myserver.public
     Public json: /etc/baltrad/exchange/crypto-keys/myserver_public.json
     

The other type that is of interest is the **keyczar** support since that provides backward compatibility with already existing installations. The keyczar-project has 
been deprecated and is not supported any longer. However, to keep the exchange working, baltrad-exchange has got it's own implementation that mimics the relevant
parts that has been used in the keyczar-library. This means that it is possible to read the public/private keys that has been generated during installation of the
baltrad software. It can also generate new keys compatible with the old installations. However, there is no support for setting up the DEX-subscription using this tool. 
 
.. code:: sh

   %> baltrad-exchange-config create_keys --type=keyczar --destination=/etc/baltrad/bltnode-keys --nodename=myserver
   Created: 
     Private key: /etc/baltrad/bltnode-keys/myserver.priv
     Public  key: /etc/baltrad/bltnode-keys/myserver.pub

create_publication
__________________

Creates a publication from the provided template and the provided property-file. If possible, the
property file will be identified by checking standard installation path. An atempt to find the
template will be used base on default location / name as well. The resulting json file should be 
possible to put in the local server config catalogue without modifications. If different sender 
protocols or different connection strategies should be used the configuration file needs to be modified
manually.

Example: baltrad-exchange-config create_publication --desturi=https://remote.baltrad.node --name="pub to remote node" --output=remote_node_publication.json

Options:
  -h, --help            show this help message and exit
  -v, --verbose         be verbose
  --conf=CONF           Specified the property file to use to extract all
                        relevant information to create the publication to
                        specified host.
  --template=TEMPLATE   The template to use for generating the publication /
                        subscription.
  --desturi=DESTURI     Specified the target of this publication
  --name=PUBLICATION_NAME
                        The name of this publication. MANDATORY!
  --output=OUTPUT       The output file name. If not specified, output will
                        printed on stdout

create_subscription
___________________

Usage: baltrad-exchange-config create_subscription [OPTIONS]

Creates a subscription package from the provided template and the provided property-file. If possible, the
property file will be identified by checking standard installation path. An atempt to find the
template will be used base on default location / name as well. The output will be a tarball containing of one 
public key and one subscription.json file and mailed to the admin for the remote server.

Example: baltrad-exchange-config create_subscription --output=subscription_bundle.tar
        

Options:
  -h, --help           show this help message and exit
  -v, --verbose        be verbose
  --conf=CONF          Specified the property file to use to extract all
                       relevant information to create the publication to
                       specified host.
  --template=TEMPLATE  The template to use for generating the publication /
                       subscription.
  --output=OUTPUT      The output file name. Must contain .tar och .tgz or
                       .tar.gz suffix. Will default to <nodename>.tar.gz


test_filter
_______________
Another useful tool is the test_filter which can be used to validate files against a filter to test how the subscription/publication filters should be defined. The matching uses the baltrad-db 
metadata querying and will generate a odim-source sqlite database so that the _bdb/source_name, _bdb/source:WMO and other bdb-specific meta attributes can be ued. This is in contrast with the naming
that instead uses _baltrad/ as prefix for internal meta data usage.

A typical filter will have a structure will look something like.

.. code:: json


  {"filter":{
    "filter_type": "and_filter", 
    "value": [
      {"filter_type": "attribute_filter", 
        "name": "_bdb/source_name", 
        "operation": "in", 
        "value_type": "string", 
        "value": ["sehem","seang", "sella"]
      }, 
      {"filter_type": "attribute_filter", 
        "name": "/what/object", 
        "operation": "in", 
        "value_type": "string", 
        "value": ["SCAN","PVOL"]
      }
    ]
  }}
 
Since this section is about the test_filter command in the config-tool we will not explain more about the filter and refer to :ref: filters.rst.

The tool requires two mandatory options and the odim-h5 file to be matched against.    

.. code:: sh

  anders@host: ~ %> baltrad-exchange-config test_filter --help
  Usage: baltrad-exchange-config COMMAND [ARGS]

  where COMMAND can be one of:
    - create_keys
    - test_filter

  to get more information about a specific command, write baltrad-exchange-config <COMMAND> --help <filename>

  Options:
    -h, --help            show this help message and exit
    -v, --verbose         be verbose
    --odim-source=ODIM_SOURCE
                          The odim source file to use for identifying the source
                          of a file. This command will create a temporary source
                          in /tmp unless underwise specified.
    --dburi=DBURI         The location where odim sources can be found. Default
                          is to create a temporary db under /tmp.
    --filter=FILTER       Specifies a file containing a filter. Can be either a
                          subscription or publication cfg-file or else a
                          separate file containing toplevel 'filter'

-----------------------
baltrad-exchange-client
-----------------------

This tool is used to communicate with the server in various ways. Examples of use can be to store files or to query for statistics and other server information.
It is possible to get available commands by running

.. code:: sh

  %> baltrad-exchange-client --help
  Usage: baltrad-exchange-client COMMAND [ARGS]

  where COMMAND can be one of:
    - batchtest
    - get_statistics
    - post_message
    - server_info
    - store

  to get more information about a specific command, write baltrad-exchange-client <COMMAND> --help


When communicating with the server it is in most cases required to provide security-related options and these options are common for all commands.

- **--conf=CONF** Specifies the configuration file to use for extracting required option values. 
  Default is to use the installations config file which usually is located under /etc/baltrad/exchange/etc/baltrad-exchange.properties

- **--noconf** Disables the usage of property file and expects all attributes to be provided on command line. Can be useful in some circumstances

- **--url=SERVER_URL** The location of the server. Usually http://localhost:8089 or https://localhost:8089.

- **-t TYPE, --type=TYPE** Type of encryption to use. Either crypto, keyczar or noauth

- **-k KEY --key=KEY** The path to the private key to sign messages with.

- **-n NAME --name=NAME** The name to use as node-name.

When the baltrad-config-client binary is executed,  url, type, key and name will be determined by reading the options from the property-file and these 
will be used as default values. Then, if the options are provided these will override the default values. This obviously will require that the user
running the baltrad-exchange-client command is allowed to read the private key.

All other options are specific to the above commands. The help section for each of the commands will explain more about how to use each command.

.. _doc-rest-cmd-batchtest:

batchtest
_________

The batchtest uses a basefile that either is a scan or a pvol and uses that as a template and then updates the source and datetime before sending it to the exchange server. It is only the
information for the swedish radars sekrn, sella, seosd, seoer, sehuv, selek, sehem, seatv, sevax, seang, sekaa and sebaa that will be set in what/source. The soure set will be in the format
WMO:02666,RAD:SE51,PLC:Karlskrona,CMT:sekaa,NOD:sekaa.

Example:

.. code:: sh

  %> baltrad-exchange-client batchtest --basefile=/data/incomming/seang_scan_202212150100_0_5.h5


.. _doc-rest-cmd-get_statistics:

get_statistics
______________

Usage: baltrad-exchange-client get_statistics [OPTIONS] --spid=STAT_ID

Queries the exchange server for various statistics information. The spid is used to identify what statistics
id that should be queried for. It is possible to query for all existing ids by executing the command
list_statistic_ids.

Example:

.. code:: sh

  %> baltrad-exchange-client get_statistics --spid=server-incomming --totals

.. _doc-rest-cmd-list_statistic_ids:

list_statistic_ids
__________________

Usage: baltrad-exchange-client list_statistic_ids [OPTIONS]

Queries the exchange server for the available statistics ids

.. code:: sh

   %> baltrad-exchange-client list_statistic_ids

.. _doc-rest-cmd-post-json-message:

post_message
____________

Usage: baltrad-exchange-client post_message [OPTIONS] MESSAGE

Posts a json message to the exchange server. Can be used to trigger for example a runnable job.

.. code:: sh

   %> baltrad-exchange-client post_message '{"trigger":"trigger_4"}'


.. _doc-rest-cmd-server_info:

server_info

Usage: baltrad-exchange-client server_info [OPTIONS]

Provides some useful information about the server. Currently the following things can be queried for.

  - uptime
    How long the server has been running

  - nodename
    The name this server is identifying itself when sending files

  - publickey
    The public key that can be used to identify myself as

.. code:: sh

   %> baltrad-exchange-client server_info uptime
        

.. _doc-rest-cmd-store-file:

store
_____

Usage: baltrad-exchange-client store [OPTIONS] FILE [ FILE]
        
Posts a sequence of files to the exchange server.
        


