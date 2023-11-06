ZeroMQ interface
================

Overview
--------------

The data transporter exchange mechanism that is used within the nordic radar exchange uses the ZeroMQ API for exchange and for ease of understanding is has been called zmq within
baltrad-exchange. This allows for a different approach of distributing files that is appreciated for it's simplicity.

The zmq assumes that the subscribers have connected to the publisher and the zmq queue doesn't monitor the transmission wether it was successful or not. This means that monitoring
of received data has to be performed on the receiving files and there is no resend (except if the ZeroMQ queue provides it) on the publisher side.

Since there is no authentication mechanisms or other features that prevents unknown subscribers the firewall has to be setup preventing this access.

Publisher
'''''''''''''''''''''''''''''''

The zmq publisher is behaving differently from the standard publisher in the way that it working as a subscribtion service and provides a listener that the subscribers can connect to. 
This means that there is no connection and/or sender associated with this publication. Instead a listening address is configured. Besides this, you can configure filters, decorators
any other feature associated with a publication, :ref:`ug_publications`. The class name of this publisher is **bexchange.net.zmq.publisher.publisher**.

The data transporter protocol expects a 256 character zero-padded filename which can be defined using namers that are decided depending on what/object as can be seen in the
below example. The filter is used if you want to distinguish what the subscribers will receive. In the below example only sehem & seang PVOLs will be published.

.. code-block:: json
   
  {
  "publication":{
     "_comment_":"ZeroMQ (datatransporter) publisher.",
     "name":"Use the internal rest protocol",
     "class":"bexchange.net.zmq.publisher.publisher",
     "extra_arguments": {
  	   "publisher_address":"tcp://*:8078",
  	   "hmac":"<change me>",
       "__namers_comment":"The namers are not required since default is to use below setting",
       "namers":[
        {"object":"SCAN","pattern":"${_baltrad/source_name}_scan_${/dataset1/where/elangle}.replace('.','_')_${/what/date}T${/what/time}.h5"},
        {"object":"default","pattern":"${_baltrad/source_name}_${/what/object}.tolower()_${/what/date}T${/what/time}.h5"}
       ]
     },
     "active":true,
     "filter":{
  	   "filter_type": "and_filter", 
  	   "value": [
  	     {"filter_type": "attribute_filter", 
  	      "name": "_bdb/source_name", 
          "operation": "in", 
          "value_type": "string", 
          "value": ["sehem","seang"]}, 
  	     {"filter_type": "attribute_filter", 
          "name": "/what/object", 
          "operation": "=", 
          "value_type": "string", 
          "value": ["PVOL"]}
       ]
      },
      "decorators":[
      ]
    }
  }

Subscribers
'''''''''''''''''''''''''''''''

The zmq subscriber is using the Zero MQ internals to setup a connection to a publisher and then passively waits until there is a message available. Due to this circumstance the
zmq subscriber is defined as a runner :ref:`ug_runners` and is run within it's own thread. The class to use is **bexchange.net.zmq.subscriber.subscriber**. In order for the
subscription to work you will have to specify a address and the hmac-key provided by the publisher. 

The subscribed data will be passed on to the engine which means that you will have to take care of the data in some other component like a storage or a publication.

**Note:** One subscription runner has to be created per remote publisher.

.. code-block:: json

  {
  "runner":{
    "_comment_":"ZMQ subscriber to localhost.'",
    "active":false,
    "class":"bexchange.net.zmq.subscriber.subscriber",
    "extra_arguments": {
      "name":"zmq - localhost",
      "hmac":"<change me>",
      "address":"tcp://127.0.0.1:8079",
    } 
  }
  }