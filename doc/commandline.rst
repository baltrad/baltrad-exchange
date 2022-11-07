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
Another useful tool is the test_filter which can be used to validate files against a filter to test how the subscription/publication filters should be defined.