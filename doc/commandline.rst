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

                          