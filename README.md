SwiftMp4
--------

SwiftMp4 Middleware for OpenStack Swift, allowing streaming of MP4s
from OpenStack Swift

Install
-------

1) Install SwiftMp4 with ``sudo python setup.py install`` or ``sudo python
   setup.py develop`` or via whatever packaging system you may be using.

2) Alter your proxy-server.conf pipeline to have swiftmp4:

If you use tempauth:

    Was::

        [pipeline:main]
        pipeline = catch_errors cache tempauth proxy-server

    Change To::

        [pipeline:main]
        pipeline = catch_errors cache swiftmp4 tempauth proxy-server

If you use keystone:

    Was::

        [pipeline:main]
        pipeline = catch_errors cache authtoken keystone proxy-server

    Change To::

        [pipeline:main]
        pipeline = catch_errors cache swiftmp4 authtoken keystone proxy-server

3) Add to your proxy-server.conf the section for the Swift3 WSGI filter::

    [filter:swiftmp4]
    use = egg:swiftmp4#swiftmp4
