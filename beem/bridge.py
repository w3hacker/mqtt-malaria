# Copyright (c) 2013, ReMake Electric ehf
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
"""
This is a module for a single message publishing process,
that publishes to it's own private bridge. The _bridge_ is configured
to bridge out to the designated target.
"""

from __future__ import division

import logging
import multiprocessing
import subprocess
import tempfile
import time

import mosquitto

import beem.load
import beem.msgs

MOSQ_BRIDGE_CFG_TEMPLATE= """
log_dest syslog
log_dest topic
log_dest stdout
bind_address 127.0.0.1
port %(local_port)d

connection mal-bridge-%(cid)s
address %(malaria_target)s
topic mqtt-malaria/# out %(qos)d
# TODO - add PSK stuff here...
"""

class BridgingSender():
    """
    A MQTT message publisher that publishes to it's own personal bridge
    """

    def __init__(self, target_host, target_port, cid):
        self.cid = cid
        self.log = logging.getLogger(__name__ + ":" + cid)

        # Generate a mosquitot bridge config
        conf_in = {
            "local_port" : 2001,
            "malaria_target": "%s:%d" % (target_host, target_port),
            "cid": cid,
            "qos": 1
        }
        conf = MOSQ_BRIDGE_CFG_TEMPLATE % conf_in
        # Save it to a temporary file
        self.mos_cfg = tempfile.NamedTemporaryFile()
        self.log.info("conf file.name is %s", self.mos_cfg.name)
        self.log.info("writing conf %s", conf)
        self.mos_cfg.write(conf)
        self.mos_cfg.seek(0)  # Make it flush...
        
        args = ["mosquitto", "-c", self.mos_cfg.name]
        self.log.info("Attempting to use args: %s", args)
        self.mos = subprocess.Popen(args)
        self.log.info("Created mosquitto...")
        time.sleep(1)
        

    def run(self, generator, qos=1):
        # Make this ts to send to our bridge...
        self.ts = beem.load.TrackingSender("localhost", 2001, self.cid)
        self.ts.run(generator, qos)
        self.log.info("killing mosquitto")
        self.mos.terminate()
        self.mos.wait()


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, stream=sys.stderr)
    b = BridgingSender("localhost", 1883, "hohoho")
    generator = beem.msgs.GaussianSize("blahblah", 10, 100)
    b.run(generator, 1)
