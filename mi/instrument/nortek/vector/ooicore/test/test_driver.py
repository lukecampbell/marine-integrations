"""
@package mi.instrument.nortek.vector.ooicore.test.test_driver
@file /Users/Bill/WorkSpace/marine-integrations/mi/instrument/nortek/vector/ooicore/driver.py
@author Bill Bollenbacher
@brief Test cases for ooicore driver

USAGE:
 Make tests verbose and provide stdout
   * From the IDK
       $ bin/test_driver
       $ bin/test_driver -u
       $ bin/test_driver -i
       $ bin/test_driver -q

   * From pyon
       $ bin/nosetests -s -v /Users/Bill/WorkSpace/marine-integrations/mi/instrument/nortek/vector/ooicore
       $ bin/nosetests -s -v /Users/Bill/WorkSpace/marine-integrations/mi/instrument/nortek/vector/ooicore -a UNIT
       $ bin/nosetests -s -v /Users/Bill/WorkSpace/marine-integrations/mi/instrument/nortek/vector/ooicore -a INT
       $ bin/nosetests -s -v /Users/Bill/WorkSpace/marine-integrations/mi/instrument/nortek/vector/ooicore -a QUAL
"""

__author__ = 'Bill Bollenbacher'
__license__ = 'Apache 2.0'

from gevent import monkey; monkey.patch_all()
import gevent
import unittest
import re
import time
import datetime
import base64
import ntplib

from nose.plugins.attrib import attr

from mi.core.log import get_logger ; log = get_logger()

# MI imports.
from mi.idk.unit_test import InstrumentDriverTestCase
from mi.idk.unit_test import InstrumentDriverUnitTestCase
from mi.idk.unit_test import InstrumentDriverIntegrationTestCase
from mi.idk.unit_test import InstrumentDriverQualificationTestCase
from mi.idk.unit_test import AgentCapabilityType

from mi.core.instrument.instrument_driver import DriverConnectionState
from mi.core.instrument.instrument_driver import DriverAsyncEvent
from mi.core.instrument.instrument_driver import DriverEvent
from mi.core.instrument.instrument_driver import DriverParameter

from mi.core.instrument.data_particle import DataParticleKey, DataParticleValue
from mi.core.instrument.chunker import StringChunker

from mi.core.exceptions import InstrumentParameterException
from mi.core.exceptions import InstrumentStateException
from mi.core.exceptions import InstrumentCommandException
from mi.core.exceptions import SampleException

from mi.instrument.nortek.vector.ooicore.driver import DataParticleType
from mi.instrument.nortek.vector.ooicore.driver import InstrumentPrompts
from mi.instrument.nortek.vector.ooicore.driver import InstrumentCmds
from mi.instrument.nortek.vector.ooicore.driver import Capability
from mi.instrument.nortek.vector.ooicore.driver import Protocol
from mi.instrument.nortek.vector.ooicore.driver import ProtocolState
from mi.instrument.nortek.vector.ooicore.driver import ProtocolEvent
from mi.instrument.nortek.vector.ooicore.driver import Parameter
from mi.instrument.nortek.vector.ooicore.driver import VectorVelocityHeaderDataParticle
from mi.instrument.nortek.vector.ooicore.driver import VectorVelocityHeaderDataParticleKey
from mi.instrument.nortek.vector.ooicore.driver import VectorVelocityDataParticle
from mi.instrument.nortek.vector.ooicore.driver import VectorVelocityDataParticleKey
from mi.instrument.nortek.vector.ooicore.driver import VectorSystemDataParticle
from mi.instrument.nortek.vector.ooicore.driver import VectorSystemDataParticleKey
from mi.instrument.nortek.vector.ooicore.driver import VectorProbeCheckDataParticle
from mi.instrument.nortek.vector.ooicore.driver import VectorProbeCheckDataParticleKey

from interface.objects import AgentCommand
from interface.objects import CapabilityType

from ion.agents.instrument.instrument_agent import InstrumentAgentState
from ion.agents.instrument.direct_access.direct_access_server import DirectAccessTypes

from pyon.agent.agent import ResourceAgentEvent

###
#   Driver parameters for the tests
###
InstrumentDriverTestCase.initialize(
    driver_module='mi.instrument.nortek.vector.ooicore.driver',
    driver_class="InstrumentDriver",

    instrument_agent_resource_id = 'nortek_vector_dw_ooicore',
    instrument_agent_name = 'nortek_vector_dw_ooicore_agent',
    instrument_agent_packet_config = DataParticleType(),
    driver_startup_config = {
        Parameter.AVG_INTERVAL: 61
        }
)

params_dict = {
    Parameter.TRANSMIT_PULSE_LENGTH : int,
    Parameter.BLANKING_DISTANCE : int,
    Parameter.RECEIVE_LENGTH : int,
    Parameter.TIME_BETWEEN_PINGS : int,
    Parameter.TIME_BETWEEN_BURST_SEQUENCES : int,
    Parameter.NUMBER_PINGS : int,
    Parameter.AVG_INTERVAL : int,
    Parameter.USER_NUMBER_BEAMS : int,
    Parameter.TIMING_CONTROL_REGISTER : int,
    Parameter.POWER_CONTROL_REGISTER : int,
    Parameter.COMPASS_UPDATE_RATE : int,
    Parameter.COORDINATE_SYSTEM : int,
    Parameter.NUMBER_BINS : int,
    Parameter.BIN_LENGTH : int,
    Parameter.MEASUREMENT_INTERVAL : int,
    Parameter.DEPLOYMENT_NAME : str,
    Parameter.WRAP_MODE : int,
    Parameter.CLOCK_DEPLOY : str,
    Parameter.DIAGNOSTIC_INTERVAL : int,
    Parameter.MODE : int,
    Parameter.ADJUSTMENT_SOUND_SPEED : int,
    Parameter.NUMBER_SAMPLES_DIAGNOSTIC : int,
    Parameter.NUMBER_BEAMS_CELL_DIAGNOSTIC : int,
    Parameter.NUMBER_PINGS_DIAGNOSTIC : int,
    Parameter.MODE_TEST : int,
    Parameter.ANALOG_INPUT_ADDR : int,
    Parameter.SW_VERSION : int,
    Parameter.VELOCITY_ADJ_TABLE : str,
    Parameter.COMMENTS : str,
    Parameter.WAVE_MEASUREMENT_MODE : int,
    Parameter.DYN_PERCENTAGE_POSITION : int,
    Parameter.WAVE_TRANSMIT_PULSE : int,
    Parameter.WAVE_BLANKING_DISTANCE : int,
    Parameter.WAVE_CELL_SIZE : int,
    Parameter.NUMBER_DIAG_SAMPLES : int,
    Parameter.NUMBER_SAMPLES_PER_BURST : int,
    Parameter.ANALOG_OUTPUT_SCALE : int,
    Parameter.CORRELATION_THRESHOLD : int,
    Parameter.TRANSMIT_PULSE_LENGTH_SECOND_LAG : int,
    Parameter.QUAL_CONSTANTS : str}

def user_config1():
    # NumberSamplesPerBurst = 20, MeasurementInterval = 500
    # deployment output from the vector application
    user_config_values = "A5 00 00 01 02 00 10 00 07 00 2C 00 00 02 01 00 \
                          40 00 03 00 82 00 00 00 CC 4E 00 00 00 00 01 00 \
                          00 00 01 00 07 00 F4 01 00 00 00 00 00 00 00 00 \
                          39 28 17 14 12 12 30 2A 00 00 30 00 11 41 01 00 \
                          01 00 14 00 04 00 00 00 00 00 5E 01 02 3D 1E 3D \
                          39 3D 53 3D 6E 3D 88 3D A2 3D BB 3D D4 3D ED 3D \
                          06 3E 1E 3E 36 3E 4E 3E 65 3E 7D 3E 93 3E AA 3E \
                          C0 3E D6 3E EC 3E 02 3F 17 3F 2C 3F 41 3F 55 3F \
                          69 3F 7D 3F 91 3F A4 3F B8 3F CA 3F DD 3F F0 3F \
                          02 40 14 40 26 40 37 40 49 40 5A 40 6B 40 7C 40 \
                          8C 40 9C 40 AC 40 BC 40 CC 40 DB 40 EA 40 F9 40 \
                          08 41 17 41 25 41 33 41 42 41 4F 41 5D 41 6A 41 \
                          78 41 85 41 92 41 9E 41 AB 41 B7 41 C3 41 CF 41 \
                          DB 41 E7 41 F2 41 FD 41 08 42 13 42 1E 42 28 42 \
                          33 42 3D 42 47 42 51 42 5B 42 64 42 6E 42 77 42 \
                          80 42 89 42 91 42 9A 42 A2 42 AA 42 B2 42 BA 42 \
                          00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 \
                          00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 \
                          00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 \
                          00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 \
                          00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 \
                          00 00 00 00 00 00 00 00 1E 00 5A 00 5A 00 BC 02 \
                          32 00 00 00 00 00 00 00 07 00 00 00 00 00 00 00 \
                          00 00 00 00 00 00 01 00 00 00 00 00 2A 00 00 00 \
                          02 00 14 00 EA 01 14 00 EA 01 0A 00 05 00 00 00 \
                          40 00 40 00 02 00 0F 00 5A 00 00 00 01 00 C8 00 \
                          00 00 00 00 0F 00 EA 01 EA 01 00 00 00 00 00 00 \
                          00 00 00 00 07 12 00 80 00 40 00 00 00 00 00 00 \
                          82 00 00 00 14 00 10 00 B1 2B 00 00 00 00 02 00 \
                          14 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 \
                          00 00 00 00 00 00 00 00 00 00 00 00 00 00 0A FF \
                          CD FF 8B 00 E5 00 EE 00 0B 00 84 FF 3D FF 5A 78"
        
    user_config = ''
    for value in user_config_values.split():
        user_config += chr(int(value, 16))
    return user_config

def user_config2():
    # NumberSamplesPerBurst = 10, MeasurementInterval = 600
    # instrument user configuration from the OSU instrument itself
    user_config_values = [0xa5, 0x00, 0x00, 0x01, 0x02, 0x00, 0x10, 0x00, 0x07, 0x00, 0x2c, 0x00, 0x00, 0x02, 0x01, 0x00, 
                          0x3c, 0x00, 0x03, 0x00, 0x82, 0x00, 0x00, 0x00, 0xcc, 0x4e, 0x00, 0x00, 0x00, 0x00, 0x02, 0x00, 
                          0x01, 0x00, 0x01, 0x00, 0x07, 0x00, 0x58, 0x02, 0x34, 0x39, 0x34, 0x33, 0x00, 0x00, 0x01, 0x00, 
                          0x26, 0x42, 0x28, 0x12, 0x12, 0x09, 0xc0, 0xa8, 0x00, 0x00, 0x30, 0x00, 0x11, 0x41, 0x14, 0x00, 
                          0x01, 0x00, 0x14, 0x00, 0x04, 0x00, 0x00, 0x00, 0x20, 0x35, 0x5e, 0x01, 0x02, 0x3d, 0x1e, 0x3d, 
                          0x39, 0x3d, 0x53, 0x3d, 0x6e, 0x3d, 0x88, 0x3d, 0xa2, 0x3d, 0xbb, 0x3d, 0xd4, 0x3d, 0xed, 0x3d, 
                          0x06, 0x3e, 0x1e, 0x3e, 0x36, 0x3e, 0x4e, 0x3e, 0x65, 0x3e, 0x7d, 0x3e, 0x93, 0x3e, 0xaa, 0x3e, 
                          0xc0, 0x3e, 0xd6, 0x3e, 0xec, 0x3e, 0x02, 0x3f, 0x17, 0x3f, 0x2c, 0x3f, 0x41, 0x3f, 0x55, 0x3f, 
                          0x69, 0x3f, 0x7d, 0x3f, 0x91, 0x3f, 0xa4, 0x3f, 0xb8, 0x3f, 0xca, 0x3f, 0xdd, 0x3f, 0xf0, 0x3f, 
                          0x02, 0x40, 0x14, 0x40, 0x26, 0x40, 0x37, 0x40, 0x49, 0x40, 0x5a, 0x40, 0x6b, 0x40, 0x7c, 0x40, 
                          0x8c, 0x40, 0x9c, 0x40, 0xac, 0x40, 0xbc, 0x40, 0xcc, 0x40, 0xdb, 0x40, 0xea, 0x40, 0xf9, 0x40, 
                          0x08, 0x41, 0x17, 0x41, 0x25, 0x41, 0x33, 0x41, 0x42, 0x41, 0x4f, 0x41, 0x5d, 0x41, 0x6a, 0x41, 
                          0x78, 0x41, 0x85, 0x41, 0x92, 0x41, 0x9e, 0x41, 0xab, 0x41, 0xb7, 0x41, 0xc3, 0x41, 0xcf, 0x41, 
                          0xdb, 0x41, 0xe7, 0x41, 0xf2, 0x41, 0xfd, 0x41, 0x08, 0x42, 0x13, 0x42, 0x1e, 0x42, 0x28, 0x42, 
                          0x33, 0x42, 0x3d, 0x42, 0x47, 0x42, 0x51, 0x42, 0x5b, 0x42, 0x64, 0x42, 0x6e, 0x42, 0x77, 0x42, 
                          0x80, 0x42, 0x89, 0x42, 0x91, 0x42, 0x9a, 0x42, 0xa2, 0x42, 0xaa, 0x42, 0xb2, 0x42, 0xba, 0x42, 
                          0x33, 0x33, 0x30, 0x35, 0x2d, 0x30, 0x30, 0x31, 0x30, 0x36, 0x5f, 0x30, 0x30, 0x30, 0x30, 0x31, 
                          0x5f, 0x32, 0x38, 0x30, 0x39, 0x32, 0x30, 0x31, 0x32, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
                          0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
                          0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
                          0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
                          0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x1e, 0x00, 0x5a, 0x00, 0x5a, 0x00, 0xbc, 0x02, 
                          0x32, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x07, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
                          0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x2a, 0x00, 0x00, 0x00, 
                          0x02, 0x00, 0x14, 0x00, 0xea, 0x01, 0x14, 0x00, 0xea, 0x01, 0x0a, 0x00, 0x05, 0x00, 0x00, 0x00, 
                          0x40, 0x00, 0x40, 0x00, 0x02, 0x00, 0x0f, 0x00, 0x5a, 0x00, 0x00, 0x00, 0x01, 0x00, 0xc8, 0x00, 
                          0x00, 0x00, 0x00, 0x00, 0x0f, 0x00, 0xea, 0x01, 0xea, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
                          0x00, 0x00, 0x00, 0x00, 0x07, 0x12, 0x00, 0x80, 0x00, 0x40, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
                          0x82, 0x00, 0x00, 0x00, 0x0a, 0x00, 0x08, 0x00, 0xb1, 0x2b, 0x00, 0x00, 0x00, 0x00, 0x02, 0x00, 
                          0x06, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
                          0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x0a, 0xff, 
                          0xcd, 0xff, 0x8b, 0x00, 0xe5, 0x00, 0xee, 0x00, 0x0b, 0x00, 0x84, 0xff, 0x3d, 0xff, 0xa7, 0xff]
    
    user_config = ''
    for value in user_config_values:
        user_config += chr(value)
    return user_config
        
# probe check data particle & sample 
def probe_check_sample():
    sample_as_hex = ("a507c7012c010000d3cec0afabbbb5a9a8a29a8e"
                     "827e78716a6e7173706d6a6664655f54568d7e67"
                     "50403b3734373735323137373432333431303031"
                     "3131313133313131313232323131303030323032"
                     "3331302f2f302f2f30313131302f2f3030302f30"
                     "30303031302f2f2f30302f2f3130302f30302f2f"
                     "2f2f2f2e2e2f2f2f2f2f2f302f2f302f2f2f2f30"
                     "302f2e2e2f3030302f2f3030302f2f2f3030302f"
                     "302f2f2f302f30302f2f2f303030302f2f2f2e2e"
                     "2f2f30302f2f302f2f2f2f2f302f2f302e2f2f2f"
                     "2f2f302f2f3130302f2f302f2f2f2e2f2f2f2f2f"
                     "2f2f2f2f2f2f2f2f2f2f2f2e2f2f2f2e2e2e2f2f"
                     "2f2f2f2f2f2f2f302f302f2f2f2f2e2e2f2f2f2f"
                     "30302e2f2e2f303030302f2f2f2f2f302f2f2f2f"
                     "2f2f2f2f2f2e2f2f2f2f2f2f2f2f2f2f302f2f30"
                     "302f2f2f2f2f2f2ed3cec0afabbbb5a9a8a29a8e"
                     "827e7871696e7173706d6a6664655f55568e785f"
                     "4b3c393535383b36353435383333353231323434"
                     "3331303031303230303232313130313132313032"
                     "32323134313131302f2f302f3031303030303030"
                     "302f2f31303030302f30312f2f303030302f302f"
                     "2f2f2f2f2e2f2f2f2f30302f2f2f2f2f30302f2f"
                     "30302f302f2f2f302f2f302f30302f2f2f2f2e2f"
                     "2f2f2f2f2f2f2f2e2f30302f2f2e2f2f2f2e2f2f"
                     "2f2f2f302f2f2f2f2f2f2f302f2f2f2f2e2f2f2f"
                     "2f2f2f2f2f2f2e2f2f2f2f2f2f2f2f2e2f2e2f2f"
                     "2e2f2e2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f"
                     "2f2f2e2f2e2e2f2e30302f302f2f2f2f2f2f2f2f"
                     "2f2f2f2f2f2f2f2f2f2f2f2f2f2f2e2f2f2f2f2f"
                     "2f2f2f2e2f2f2f2f2f2f2f2f2f2e2e2e2f2f2e2e"
                     "2f2f2f2e2f2e2f2fd3cec0afaabbb5a9a8a19a8e"
                     "827e7871696e7173706d6a6664655f5556877860"
                     "4a3c363233363637363637363334373833343435"
                     "32302f303334383534313034353834313231302f"
                     "3030312f32313031303232323734323133343532"
                     "3132323032313030313135353234313131323131"
                     "2f303131303131333030302f30302f2f30313232"
                     "31302f2f3030302f2f2f2f2f302f2e2e2f2e2e2f"
                     "2f302f2f2f2e2e2f2f2f302f2f2f2f302f2f2f2f"
                     "2f2f2e2f2f2f302f2f2e2f2f2e2e2f30302e2e2e"
                     "2f2f2e2e2f2f2f2f2f2f2f2f2e2e2f2f2e2e2f2f"
                     "2f302f2e2e2f2f2f2f2f2e2f2f302f2f2e2e2f2e"
                     "2f2f2e2f2f2f2f2f2f2e2e2e2e302f2f2f2f2e2f"
                     "2e2e2e2f2e2e2e2f2e2e2e2f2e2e2e2f2f2f2f2f"
                     "2e2e2e2e2f2e2e2f2f2e2f2f2f2f2e2e2f2f2f2f"
                     "2e2f2f2f2f2f2f2ffd74")
    return sample_as_hex.decode('hex')

# these values checkout against the sample above
probe_check_particle = [{'value_id': 'number_of_samples_per_beam',  'value': 300},
                        {'value_id': 'first_sample_number',  'value': 0},
                        {'value_id': 'beam_1_amplitudes',  'value': [211, 206, 192, 175, 171, 187, 181, 169, 168, 162, 154, 142, 130, 126, 120, 113, 106, 110, 113, 115, 
                                                                     112, 109, 106, 102, 100, 101, 95, 84, 86, 141, 126, 103, 80, 64, 59, 55, 52, 55, 55, 53, 50, 49, 
                                                                     55, 55, 52, 50, 51, 52, 49, 48, 48, 49, 49, 49, 49, 49, 51, 49, 49, 49, 49, 50, 50, 50, 49, 49, 48, 
                                                                     48, 48, 50, 48, 50, 51, 49, 48, 47, 47, 48, 47, 47, 48, 49, 49, 49, 48, 47, 47, 48, 48, 48, 47, 48, 
                                                                     48, 48, 48, 49, 48, 47, 47, 47, 48, 48, 47, 47, 49, 48, 48, 47, 48, 48, 47, 47, 47, 47, 47, 46, 46, 
                                                                     47, 47, 47, 47, 47, 47, 48, 47, 47, 48, 47, 47, 47, 47, 48, 48, 47, 46, 46, 47, 48, 48, 48, 47, 47, 
                                                                     48, 48, 48, 47, 47, 47, 48, 48, 48, 47, 48, 47, 47, 47, 48, 47, 48, 48, 47, 47, 47, 48, 48, 48, 48, 
                                                                     47, 47, 47, 46, 46, 47, 47, 48, 48, 47, 47, 48, 47, 47, 47, 47, 47, 48, 47, 47, 48, 46, 47, 47, 47, 
                                                                     47, 47, 48, 47, 47, 49, 48, 48, 47, 47, 48, 47, 47, 47, 46, 47, 47, 47, 47, 47, 47, 47, 47, 47, 47, 
                                                                     47, 47, 47, 47, 47, 47, 46, 47, 47, 47, 46, 46, 46, 47, 47, 47, 47, 47, 47, 47, 47, 47, 48, 47, 48, 
                                                                     47, 47, 47, 47, 46, 46, 47, 47, 47, 47, 48, 48, 46, 47, 46, 47, 48, 48, 48, 48, 47, 47, 47, 47, 47, 
                                                                     48, 47, 47, 47, 47, 47, 47, 47, 47, 47, 46, 47, 47, 47, 47, 47, 47, 47, 47, 47, 47, 48, 47, 47, 48, 
                                                                     48, 47, 47, 47, 47, 47, 47, 46]},
                        {'value_id': 'beam_2_amplitudes',  'value': [211, 206, 192, 175, 171, 187, 181, 169, 168, 162, 154, 142, 130, 126, 120, 113, 105, 110, 113, 115, 
                                                                     112, 109, 106, 102, 100, 101, 95, 85, 86, 142, 120, 95, 75, 60, 57, 53, 53, 56, 59, 54, 53, 52, 53, 
                                                                     56, 51, 51, 53, 50, 49, 50, 52, 52, 51, 49, 48, 48, 49, 48, 50, 48, 48, 50, 50, 49, 49, 48, 49, 49, 
                                                                     50, 49, 48, 50, 50, 50, 49, 52, 49, 49, 49, 48, 47, 47, 48, 47, 48, 49, 48, 48, 48, 48, 48, 48, 48, 
                                                                     47, 47, 49, 48, 48, 48, 48, 47, 48, 49, 47, 47, 48, 48, 48, 48, 47, 48, 47, 47, 47, 47, 47, 46, 47, 
                                                                     47, 47, 47, 48, 48, 47, 47, 47, 47, 47, 48, 48, 47, 47, 48, 48, 47, 48, 47, 47, 47, 48, 47, 47, 48, 
                                                                     47, 48, 48, 47, 47, 47, 47, 46, 47, 47, 47, 47, 47, 47, 47, 47, 46, 47, 48, 48, 47, 47, 46, 47, 47, 
                                                                     47, 46, 47, 47, 47, 47, 47, 48, 47, 47, 47, 47, 47, 47, 47, 48, 47, 47, 47, 47, 46, 47, 47, 47, 47, 
                                                                     47, 47, 47, 47, 47, 46, 47, 47, 47, 47, 47, 47, 47, 47, 46, 47, 46, 47, 47, 46, 47, 46, 47, 47, 47, 
                                                                     47, 47, 47, 47, 47, 47, 47, 47, 47, 47, 47, 47, 47, 47, 47, 47, 46, 47, 46, 46, 47, 46, 48, 48, 47, 
                                                                     48, 47, 47, 47, 47, 47, 47, 47, 47, 47, 47, 47, 47, 47, 47, 47, 47, 47, 47, 47, 47, 47, 47, 46, 47, 
                                                                     47, 47, 47, 47, 47, 47, 47, 46, 47, 47, 47, 47, 47, 47, 47, 47, 47, 46, 46, 46, 47, 47, 46, 46, 47, 
                                                                     47, 47, 46, 47, 46, 47, 47]},
                        {'value_id': 'beam_3_amplitudes',  'value': [211, 206, 192, 175, 170, 187, 181, 169, 168, 161, 154, 142, 130, 126, 120, 113, 105, 110, 113, 115, 
                                                                     112, 109, 106, 102, 100, 101, 95, 85, 86, 135, 120, 96, 74, 60, 54, 50, 51, 54, 54, 55, 54, 54, 55, 
                                                                     54, 51, 52, 55, 56, 51, 52, 52, 53, 50, 48, 47, 48, 51, 52, 56, 53, 52, 49, 48, 52, 53, 56, 52, 49, 
                                                                     50, 49, 48, 47, 48, 48, 49, 47, 50, 49, 48, 49, 48, 50, 50, 50, 55, 52, 50, 49, 51, 52, 53, 50, 49, 
                                                                     50, 50, 48, 50, 49, 48, 48, 49, 49, 53, 53, 50, 52, 49, 49, 49, 50, 49, 49, 47, 48, 49, 49, 48, 49, 
                                                                     49, 51, 48, 48, 48, 47, 48, 48, 47, 47, 48, 49, 50, 50, 49, 48, 47, 47, 48, 48, 48, 47, 47, 47, 47, 
                                                                     47, 48, 47, 46, 46, 47, 46, 46, 47, 47, 48, 47, 47, 47, 46, 46, 47, 47, 47, 48, 47, 47, 47, 47, 48, 
                                                                     47, 47, 47, 47, 47, 47, 46, 47, 47, 47, 48, 47, 47, 46, 47, 47, 46, 46, 47, 48, 48, 46, 46, 46, 47, 
                                                                     47, 46, 46, 47, 47, 47, 47, 47, 47, 47, 47, 46, 46, 47, 47, 46, 46, 47, 47, 47, 48, 47, 46, 46, 47, 
                                                                     47, 47, 47, 47, 46, 47, 47, 48, 47, 47, 46, 46, 47, 46, 47, 47, 46, 47, 47, 47, 47, 47, 47, 46, 46, 
                                                                     46, 46, 48, 47, 47, 47, 47, 46, 47, 46, 46, 46, 47, 46, 46, 46, 47, 46, 46, 46, 47, 46, 46, 46, 47, 
                                                                     47, 47, 47, 47, 46, 46, 46, 46, 47, 46, 46, 47, 47, 46, 47, 47, 47, 47, 46, 46, 47, 47, 47, 47, 46, 
                                                                     47, 47, 47, 47, 47, 47, 47]},
                        ]
# velocity data particle & sample 
def velocity_sample():
    sample_as_hex = "a51000db00008f10000049f041f72303303132120918d8f7"
    return sample_as_hex.decode('hex')

# these values checkout against the sample above
velocity_particle = [{'value_id': 'analog_input2', 'value': 0}, 
                     {'value_id': 'count', 'value': 219}, 
                     {'value_id': 'pressure', 'value': 4239}, 
                     {'value_id': 'analog_input1', 'value': 0}, 
                     {'value_id': 'velocity_beam1', 'value': 61513}, 
                     {'value_id': 'velocity_beam2', 'value': 63297}, 
                     {'value_id': 'velocity_beam3', 'value': 803}, 
                     {'value_id': 'amplitude_beam1', 'value': 48}, 
                     {'value_id': 'amplitude_beam2', 'value': 49}, 
                     {'value_id': 'amplitude_beam3', 'value': 50}, 
                     {'value_id': 'correlation_beam1', 'value': 18}, 
                     {'value_id': 'correlation_beam2', 'value': 9}, 
                     {'value_id': 'correlation_beam3', 'value': 24}]

# velocity header data particle & sample 
def velocity_header_sample():
    sample_as_hex = "a512150012491711121270032f2f2e0002090d0000000000000000000000000000000000000000005d70"
    return sample_as_hex.decode('hex')

# these values checkout against the sample above
velocity_header_particle = [{'value_id': 'timestamp', 'value': '17/12/2012 11:12:49'}, 
                            {'value_id': 'number_of_records', 'value': 880}, 
                            {'value_id': 'noise1', 'value': 47}, 
                            {'value_id': 'noise2', 'value': 47}, 
                            {'value_id': 'noise3', 'value': 46}, 
                            {'value_id': 'correlation1', 'value': 2}, 
                            {'value_id': 'correlation2', 'value': 9}, 
                            {'value_id': 'correlation3', 'value': 13}]

# system data particle & sample 
def system_sample():
    sample_as_hex = "a5110e0003261317121294007c3b83041301cdfe0a08007b0000e4d9"
    return sample_as_hex.decode('hex')

# these values checkout against the sample above
system_particle = [{'value_id': 'timestamp', 'value': '13/12/2012 17:03:26'}, 
                   {'value_id': 'battery', 'value': 148}, 
                   {'value_id': 'sound_speed', 'value': 15228}, 
                   {'value_id': 'heading', 'value': 1155}, 
                   {'value_id': 'pitch', 'value': 275}, 
                   {'value_id': 'roll', 'value': 65229}, 
                   {'value_id': 'temperature', 'value': 2058}, 
                   {'value_id': 'error', 'value': 0}, 
                   {'value_id': 'status', 'value': 123}, 
                   {'value_id': 'analog_input', 'value': 0}]


#################################### RULES ####################################
#                                                                             #
# Common capabilities in the base class                                       #
#                                                                             #
# Instrument specific stuff in the derived class                              #
#                                                                             #
# Generator spits out either stubs or comments describing test this here,     #
# test that there.                                                            #
#                                                                             #
# Qualification tests are driven through the instrument_agent                 #
#                                                                             #
###############################################################################


###############################################################################
#                                UNIT TESTS                                   #
#         Unit tests test the method calls and parameters using Mock.         #
###############################################################################
@attr('UNIT', group='mi')
class UnitFromIDK(InstrumentDriverUnitTestCase):
    def setUp(self):
        InstrumentDriverUnitTestCase.setUp(self)

    def assert_chunker_fragmented_sample(self, chunker, fragments, sample):
        '''
        Verify the chunker can parse a sample that comes in fragmented
        @param chunker: Chunker to use to do the parsing
        @param sample: raw sample
        '''
        timestamps = []
        for f in fragments:
            ts = self.get_ntp_timestamp()
            timestamps.append(ts)
            chunker.add_chunk(f, ts)
            (timestamp, result) = chunker.get_next_data()
            if (result): break

        self.assertEqual(result, sample)
        self.assertEqual(timestamps[0], timestamp)

        (timestamp, result) = chunker.get_next_data()
        self.assertEqual(result, None)

    def assert_chunker_combined_sample(self, chunker, sample1, sample2, sample3):
        '''
        Verify the chunker can parse samples that comes in combined
        @param chunker: Chunker to use to do the parsing
        @param sample: raw sample
        '''
        ts = self.get_ntp_timestamp()
        chunker.add_chunk(sample1 + sample2 + sample3, ts)

        (timestamp, result) = chunker.get_next_data()
        self.assertEqual(result, sample1)
        self.assertEqual(ts, timestamp)

        (timestamp, result) = chunker.get_next_data()
        self.assertEqual(result, sample2)
        self.assertEqual(ts, timestamp)

        (timestamp, result) = chunker.get_next_data()
        self.assertEqual(result, sample3)
        self.assertEqual(ts, timestamp)

        (timestamp,result) = chunker.get_next_data()
        self.assertEqual(result, None)
        
    def test_instrumment_prompts_for_duplicates(self):
        """
        Verify that the InstrumentPrompts enumeration has no duplicate values that might cause confusion
        """
        self.assert_enum_has_no_duplicates(InstrumentPrompts())


    def test_instrument_commands_for_duplicates(self):
        """
        Verify that the InstrumentCmds enumeration has no duplicate values that might cause confusion
        """
        self.assert_enum_has_no_duplicates(InstrumentCmds())

    def test_protocol_state_for_duplicates(self):
        """
        Verify that the ProtocolState enumeration has no duplicate values that might cause confusion
        """
        self.assert_enum_has_no_duplicates(ProtocolState())

    def test_protocol_event_for_duplicates(self):
        """
        Verify that the ProtocolEvent enumeration has no duplicate values that might cause confusion
        """
        self.assert_enum_has_no_duplicates(ProtocolEvent())

    def test_capability_for_duplicates(self):
        """
        Verify that the Capability enumeration has no duplicate values that might cause confusion
        """
        self.assert_enum_has_no_duplicates(Capability())

    def test_parameter_for_duplicates(self):
        """
        Verify that the Parameter enumeration has no duplicate values that might cause confusion
        """
        self.assert_enum_has_no_duplicates(Parameter())

    def test_velocity_header_sample_format(self):
        """
        Test to make sure we can get velocity_header sample data out in a reasonable format.
        Parsed is all we care about...raw is tested in the base DataParticle tests
        """
        
        port_timestamp = 3555423720.711772
        driver_timestamp = 3555423722.711772
        text_timestamp = time.strptime('17/12/2012 11:12:49', "%d/%m/%Y %H:%M:%S")
        internal_timestamp = ntplib.system_to_ntp_time(time.mktime(text_timestamp))
 
        # construct the expected particle
        expected_particle = {
            DataParticleKey.PKT_FORMAT_ID: DataParticleValue.JSON_DATA,
            DataParticleKey.PKT_VERSION: 1,
            DataParticleKey.STREAM_NAME: DataParticleType.VELOCITY_HEADER,
            DataParticleKey.PORT_TIMESTAMP: port_timestamp,
            DataParticleKey.DRIVER_TIMESTAMP: driver_timestamp,
            DataParticleKey.INTERNAL_TIMESTAMP: internal_timestamp,
            DataParticleKey.PREFERRED_TIMESTAMP: DataParticleKey.PORT_TIMESTAMP,
            DataParticleKey.QUALITY_FLAG: DataParticleValue.OK,
            DataParticleKey.VALUES: velocity_header_particle
            }
        
        self.compare_parsed_data_particle(VectorVelocityHeaderDataParticle,
                                          velocity_header_sample(),
                                          expected_particle)

    @unittest.skip("failed unit test.")
    def test_velocity_sample_format(self):
        """
        Test to make sure we can get velocity sample data out in a reasonable format.
        Parsed is all we care about...raw is tested in the base DataParticle tests
        """
        
        port_timestamp = 3555423720.711772
        driver_timestamp = 3555423722.711772

        # construct the expected particle
        expected_particle = {
            DataParticleKey.PKT_FORMAT_ID: DataParticleValue.JSON_DATA,
            DataParticleKey.PKT_VERSION: 1,
            DataParticleKey.STREAM_NAME: DataParticleType.VELOCITY,
            DataParticleKey.PORT_TIMESTAMP: port_timestamp,
            DataParticleKey.DRIVER_TIMESTAMP: driver_timestamp,
            DataParticleKey.PREFERRED_TIMESTAMP: DataParticleKey.PORT_TIMESTAMP,
            DataParticleKey.QUALITY_FLAG: DataParticleValue.OK,
            DataParticleKey.VALUES: velocity_particle
            }
        
        self.compare_parsed_data_particle(VectorVelocityDataParticle,
                                          velocity_sample(),
                                          expected_particle)

    def test_system_sample_format(self):
        """
        Test to make sure we can get velocity sample data out in a reasonable format.
        Parsed is all we care about...raw is tested in the base DataParticle tests
        """
        
        port_timestamp = 3555423720.711772
        driver_timestamp = 3555423722.711772
        text_timestamp = time.strptime('13/12/2012 17:03:26', "%d/%m/%Y %H:%M:%S")
        internal_timestamp = ntplib.system_to_ntp_time(time.mktime(text_timestamp))

        # construct the expected particle
        expected_particle = {
            DataParticleKey.PKT_FORMAT_ID: DataParticleValue.JSON_DATA,
            DataParticleKey.PKT_VERSION: 1,
            DataParticleKey.STREAM_NAME: DataParticleType.SYSTEM,
            DataParticleKey.PORT_TIMESTAMP: port_timestamp,
            DataParticleKey.DRIVER_TIMESTAMP: driver_timestamp,
            DataParticleKey.INTERNAL_TIMESTAMP: internal_timestamp,
            DataParticleKey.PREFERRED_TIMESTAMP: DataParticleKey.PORT_TIMESTAMP,
            DataParticleKey.QUALITY_FLAG: DataParticleValue.OK,
            DataParticleKey.VALUES: system_particle
            }
        
        self.compare_parsed_data_particle(VectorSystemDataParticle,
                                          system_sample(),
                                          expected_particle)

    def test_probe_check_sample_format(self):
        """
        Test to make sure we can get probe check sample data out in a reasonable format.
        Parsed is all we care about...raw is tested in the base DataParticle tests
        """
        
        port_timestamp = 3555423720.711772
        driver_timestamp = 3555423722.711772

        # construct the expected particle
        expected_particle = {
            DataParticleKey.PKT_FORMAT_ID: DataParticleValue.JSON_DATA,
            DataParticleKey.PKT_VERSION: 1,
            DataParticleKey.STREAM_NAME: DataParticleType.PROBE_CHECK,
            DataParticleKey.PORT_TIMESTAMP: port_timestamp,
            DataParticleKey.DRIVER_TIMESTAMP: driver_timestamp,
            DataParticleKey.PREFERRED_TIMESTAMP: DataParticleKey.PORT_TIMESTAMP,
            DataParticleKey.QUALITY_FLAG: DataParticleValue.OK,
            DataParticleKey.VALUES: probe_check_particle
            }
        
        self.compare_parsed_data_particle(VectorProbeCheckDataParticle,
                                          probe_check_sample(),
                                          expected_particle)

    def test_chunker(self):
        """
        Tests the chunker
        """
        chunker = StringChunker(Protocol.chunker_sieve_function)

        # test complete data structures
        self.assert_chunker_sample(chunker, velocity_sample())
        self.assert_chunker_sample(chunker, system_sample())
        self.assert_chunker_sample(chunker, velocity_header_sample())
        self.assert_chunker_sample(chunker, probe_check_sample())

        # test fragmented data structures
        sample = velocity_sample()
        fragments = [sample[0:4], sample[4:10], sample[10:14], sample[14:]]
        self.assert_chunker_fragmented_sample(chunker, fragments, sample)

        sample = system_sample()
        fragments = [sample[0:5], sample[5:11], sample[11:15], sample[15:]]
        self.assert_chunker_fragmented_sample(chunker, fragments, sample)

        sample = velocity_header_sample()
        fragments = [sample[0:3], sample[3:11], sample[11:12], sample[12:]]
        self.assert_chunker_fragmented_sample(chunker, fragments, sample)

        sample = probe_check_sample()
        fragments = [sample[0:30], sample[30:110], sample[110:220], sample[220:500], sample[500:800], sample[800:]]
        self.assert_chunker_fragmented_sample(chunker, fragments, sample)

        # test combined data structures
        self.assert_chunker_combined_sample(chunker, velocity_sample(), system_sample(), velocity_header_sample())
        self.assert_chunker_combined_sample(chunker, velocity_header_sample(), velocity_sample(), system_sample())
        self.assert_chunker_combined_sample(chunker, velocity_header_sample(), probe_check_sample(), system_sample())

        # test data structures with noise
        self.assert_chunker_sample_with_noise(chunker, velocity_sample())
        self.assert_chunker_sample_with_noise(chunker, system_sample())
        self.assert_chunker_sample_with_noise(chunker, velocity_header_sample())
        self.assert_chunker_sample_with_noise(chunker, probe_check_sample())

    def test_corrupt_data_structures(self):
        # garbage is not okay
        particle = VectorVelocityHeaderDataParticle(velocity_header_sample().replace(chr(0), chr(1), 1),
                                                          port_timestamp = 3558720820.531179)
        with self.assertRaises(SampleException):
            particle.generate()
         
        particle = VectorSystemDataParticle(system_sample().replace(chr(0), chr(1), 1),
                                                          port_timestamp = 3558720820.531179)
        with self.assertRaises(SampleException):
            particle.generate()
         
        particle = VectorVelocityDataParticle(velocity_sample().replace(chr(16), chr(17), 1),
                                                          port_timestamp = 3558720820.531179)
        with self.assertRaises(SampleException):
            particle.generate()
         
        particle = VectorProbeCheckDataParticle(velocity_sample().replace(chr(16), chr(17), 1),
                                                          port_timestamp = 3558720820.531179)
        with self.assertRaises(SampleException):
            particle.generate()
         
 
###############################################################################
#                            INTEGRATION TESTS                                #
#     Integration test test the direct driver / instrument interaction        #
#     but making direct calls via zeromq.                                     #
#     - Common Integration tests test the driver through the instrument agent #
#     and common for all drivers (minimum requirement for ION ingestion)      #
###############################################################################
@attr('INT', group='mi')
class IntFromIDK(InstrumentDriverIntegrationTestCase):
    
    protocol_state = ''
    
    def setUp(self):
        InstrumentDriverIntegrationTestCase.setUp(self)

    def assertParamDictionariesEqual(self, pd1, pd2, all_params=False):
        """
        Verify all device parameters exist and are correct type.
        """
        if all_params:
            self.assertEqual(set(pd1.keys()), set(pd2.keys()))
            #print str(pd1)
            #print str(pd2)
            for (key, type_val) in pd2.iteritems():
                #print key
                #print type_val
                self.assertTrue(isinstance(pd1[key], type_val))
        else:
            for (key, val) in pd1.iteritems():
                self.assertTrue(pd2.has_key(key))
                self.assertTrue(isinstance(val, pd2[key]))
    
    def check_state(self, expected_state):
        self.protocol_state = self.driver_client.cmd_dvr('get_resource_state')
        self.assertEqual(self.protocol_state, expected_state)
        return 
        
    def put_driver_in_command_mode(self):
        """Wrap the steps and asserts for going into command mode.
           May be used in multiple test cases.
        """
        # Test that the driver is in state unconfigured.
        self.check_state(DriverConnectionState.UNCONFIGURED)

        # Configure driver and transition to disconnected.
        self.driver_client.cmd_dvr('configure', self.port_agent_comm_config())

        # Test that the driver is in state disconnected.
        self.check_state(DriverConnectionState.DISCONNECTED)

        # Setup the protocol state machine and the connection to port agent.
        self.driver_client.cmd_dvr('connect')

        # Test that the driver protocol is in state unknown.
        self.check_state(ProtocolState.UNKNOWN)

        # Discover what state the instrument is in and set the protocol state accordingly.
        self.driver_client.cmd_dvr('discover_state')

        try:
            # Test that the driver protocol is in state command.
            self.check_state(ProtocolState.COMMAND)
        except:
            self.assertEqual(self.protocol_state, ProtocolState.AUTOSAMPLE)
            # Put the driver in command mode
            self.driver_client.cmd_dvr('execute_resource', ProtocolEvent.STOP_AUTOSAMPLE)
            # Test that the driver protocol is in state command.
            self.check_state(ProtocolState.COMMAND)

 
    def test_set_init_params(self):
        """
        @brief Test for set_init_params()
        """
        self.put_driver_in_command_mode()

        values_before = self.driver_client.cmd_dvr('get_resource', Parameter.ALL)
        
        self.driver_client.cmd_dvr('set_init_params', {DriverParameter.ALL: base64.b64encode(user_config1())})
        self.driver_client.cmd_dvr("apply_startup_params") 

        values_after = self.driver_client.cmd_dvr("get_resource", Parameter.ALL)

        # check to see if startup config got set in instrument
        self.assertEquals(values_after[Parameter.MEASUREMENT_INTERVAL], 500)
        self.assertEquals(values_after[Parameter.NUMBER_SAMPLES_PER_BURST], 20)

        self.driver_client.cmd_dvr('set_resource', values_before)
        values_after = self.driver_client.cmd_dvr('get_resource', Parameter.ALL)
        self.assertEquals(values_after, values_before)
        
        

    def test_startup_configuration(self):
        '''
        Test that the startup configuration is applied correctly
        '''
        self.put_driver_in_command_mode()

        value_before = self.driver_client.cmd_dvr('get_resource', [Parameter.AVG_INTERVAL])
    
        self.driver_client.cmd_dvr('apply_startup_params')

        reply = self.driver_client.cmd_dvr('get_resource', [Parameter.AVG_INTERVAL])

        self.assertEquals(reply, {Parameter.AVG_INTERVAL: 61})

        reply = self.driver_client.cmd_dvr('set_resource', value_before)

        reply = self.driver_client.cmd_dvr('get_resource', [Parameter.AVG_INTERVAL])

        self.assertEquals(reply, value_before)


    def test_instrument_wakeup(self):
        """
        @brief Test for instrument wakeup, puts instrument in 'command' state
        """
        self.put_driver_in_command_mode()


    def test_instrument_clock_sync(self):
        """
        @brief Test for syncing clock
        """
        
        self.put_driver_in_command_mode()
        
        # command the instrument to read the clock.
        response = self.driver_client.cmd_dvr('execute_resource', ProtocolEvent.READ_CLOCK)
        
        log.debug("read clock returned: %s", response)
        self.assertTrue(re.search(r'.*/.*/.*:.*:.*', response[1]))

        # command the instrument to sync the clck.
        self.driver_client.cmd_dvr('execute_resource', ProtocolEvent.CLOCK_SYNC)

        # command the instrument to read the clock.
        response = self.driver_client.cmd_dvr('execute_resource', ProtocolEvent.READ_CLOCK)
        
        log.debug("read clock returned: %s", response)
        self.assertTrue(re.search(r'.*/.*/.*:.*:.*', response[1]))
        
        # verify that the dates match 
        local_time = time.gmtime(time.mktime(time.localtime()))
        local_time_str = time.strftime("%d/%m/%Y %H:%M:%S", local_time)
        self.assertTrue(local_time_str[:12].upper() in response[1].upper())
        
        # verify that the times match closely
        instrument_time = time.strptime(response[1], '%d/%m/%Y %H:%M:%S')
        #log.debug("it=%s, lt=%s" %(instrument_time, local_time))
        it = datetime.datetime(*instrument_time[:6])
        lt = datetime.datetime(*local_time[:6])
        #log.debug("it=%s, lt=%s, lt-it=%s" %(it, lt, lt-it))
        if lt - it > datetime.timedelta(seconds = 5):
            self.fail("time delta too large after clock sync")      

    def test_instrument_set_configuration(self):
        """
        @brief Test for setting instrument configuration
        """
        
        self.put_driver_in_command_mode()
        
        # command the instrument to set the user configuration.
        self.driver_client.cmd_dvr('execute_resource', ProtocolEvent.SET_CONFIGURATION, user_configuration=base64.b64encode(user_config2()))
        
        values_after = self.driver_client.cmd_dvr("get_resource", Parameter.ALL)
        #print("va=%s" %values_after)
        
        # check to see if config got set in instrument
        self.assertEquals(values_after[Parameter.MEASUREMENT_INTERVAL], 600)
        self.assertEquals(values_after[Parameter.NUMBER_SAMPLES_PER_BURST], 10)
         

    def test_instrument_read_clock(self):
        """
        @brief Test for reading instrument clock
        """
        self.put_driver_in_command_mode()
        
        # command the instrument to read the clock.
        response = self.driver_client.cmd_dvr('execute_resource', ProtocolEvent.READ_CLOCK)
        
        log.debug("read clock returned: %s", response)
        self.assertTrue(re.search(r'.*/.*/.*:.*:.*', response[1]))
 

    def test_instrument_read_mode(self):
        """
        @brief Test for reading what mode
        """
        self.put_driver_in_command_mode()
        
        # command the instrument to read the mode.
        response = self.driver_client.cmd_dvr('execute_resource', ProtocolEvent.READ_MODE)
        
        log.debug("what mode returned: %s", response)
        self.assertTrue(2, response[1])


    def test_instrument_power_down(self):
        """
        @brief Test for power_down
        """
        self.put_driver_in_command_mode()
        
        # command the instrument to power down.
        self.driver_client.cmd_dvr('execute_resource', ProtocolEvent.POWER_DOWN)
        

    def test_instrument_read_battery_voltage(self):
        """
        @brief Test for reading battery voltage
        """
        self.put_driver_in_command_mode()
        
        # command the instrument to read the battery voltage.
        response = self.driver_client.cmd_dvr('execute_resource', ProtocolEvent.READ_BATTERY_VOLTAGE)
        
        log.debug("read battery voltage returned: %s", response)
        self.assertTrue(isinstance(response[1], int))


    def test_instrument_read_id(self):
        """
        @brief Test for reading ID
        """
        self.put_driver_in_command_mode()
        
        # command the instrument to read the ID.
        response = self.driver_client.cmd_dvr('execute_resource', ProtocolEvent.READ_ID)
        
        log.debug("read ID returned: %s", response)
        self.assertTrue(re.search(r'VEC 8181.*', response[1]))


    def test_instrument_read_fat(self):
        """
        @brief Test for reading FAT
        """
        self.put_driver_in_command_mode()
        
        # command the instrument to read the FAT.
        response = self.driver_client.cmd_dvr('execute_resource', ProtocolEvent.READ_FAT)
        
        log.debug("read ID returned:")
        for item in response[1]:
            log.debug("%s", item)


    def test_instrument_read_hw_config(self):
        """
        @brief Test for reading HW config
        """
        
        hw_config = {'Status': 4, 
                     'RecSize': 144, 
                     'SerialNo': 'VEC 8181      ', 
                     'FWversion': '3.36', 
                     'Frequency': 65535, 
                     'PICversion': 0, 
                     'HWrevision': 4, 
                     'Config': 4}        
        
        self.put_driver_in_command_mode()
        
        # command the instrument to read the hw config.
        response = self.driver_client.cmd_dvr('execute_resource', ProtocolEvent.GET_HW_CONFIGURATION)
        
        log.debug("read HW config returned: %s", response)
        self.assertEqual(hw_config, response[1])


    def test_instrument_read_head_config(self):
        """
        @brief Test for reading HEAD config
        """
        
        head_config = {'Config': 55, 
                       'SerialNo': 'VEC 4943\x00\x00\x00\x00', 
                       'System': 'AAAAAAAAAACZKsPqq+oOABkl29p4BYMFiQUcvQ0Agivs/x2/BfwiK0IAoA8AAAAA//8AAP//AAD//wAAAAAAAAAA//8AAAEAAAABAAAAAAAAAP////8AAAAA//8BAAAAAAAZAKL2WRTJBQMB2BtaKp2f/vw1Ml0Ae55P/5IyTACYfgr9SP8K/VR9KwHP/jYC/3/6//f/+v8AAAAAAAAAAAAAAAAAAAAAnxQQDhAOECc=', 
                       'Frequency': 6000, 
                       'NBeams': 3, 
                       'Type': 1}

        self.put_driver_in_command_mode()
        
        # command the instrument to read the head config.
        response = self.driver_client.cmd_dvr('execute_resource', ProtocolEvent.GET_HEAD_CONFIGURATION)
        
        log.debug("read HEAD config returned: %s", response)
        self.assertEqual(head_config, response[1])


    @unittest.skip("skip until issue with instrument recorder resolved, command fails with NACK from instrument")
    def test_instrument_start_measurement_immediate(self):
        """
        @brief Test for starting measurement immediate
        """
        self.put_driver_in_command_mode()
        
        # command the instrument to start measurement immediate.
        self.driver_client.cmd_dvr('execute_resource', ProtocolEvent.START_MEASUREMENT_IMMEDIATE)
        gevent.sleep(100)  # wait for measurement to complete               


    @unittest.skip("skip until issue with instrument recorder resolved, command fails with NACK from instrument")
    def test_instrument_start_measurement_at_specific_time(self):
        """
        @brief Test for starting measurement immediate
        """
        self.put_driver_in_command_mode()
        
        # command the instrument to start measurement immediate.
        self.driver_client.cmd_dvr('execute_resource', ProtocolEvent.START_MEASUREMENT_AT_SPECIFIC_TIME)
        gevent.sleep(100)  # wait for measurement to complete               


    def test_instrument_set(self):
        """
        @brief Test for setting instrument parameter
        """
        self.put_driver_in_command_mode()

        # Get all device parameters. Confirm all expected keys are retrieved
        # and have correct type.
        reply = self.driver_client.cmd_dvr('get_resource', Parameter.ALL)
        self.assertParamDictionariesEqual(reply, params_dict, True)

        # Grab a subset of parameters.
        params = [
            Parameter.WRAP_MODE
            ]
        reply = self.driver_client.cmd_dvr('get_resource', params)
        #self.assertParamDict(reply)        

        # Remember the original subset.
        orig_params = reply
        
        # Construct new parameters to set.
        new_wrap_mode = 1 if orig_params[Parameter.WRAP_MODE]==0 else 0
        log.debug('old=%d, new=%d' %(orig_params[Parameter.WRAP_MODE], new_wrap_mode))
        new_params = {
            Parameter.WRAP_MODE : new_wrap_mode
        }
        
        # Set parameter and verify.
        reply = self.driver_client.cmd_dvr('set_resource', new_params)
        
        reply = self.driver_client.cmd_dvr('get_resource', params)
        self.assertEqual(new_params[Parameter.WRAP_MODE], reply[Parameter.WRAP_MODE])

        # Reset parameter to original value and verify.
        reply = self.driver_client.cmd_dvr('set_resource', orig_params)
        
        reply = self.driver_client.cmd_dvr('get_resource', params)
        self.assertEqual(orig_params[Parameter.WRAP_MODE], reply[Parameter.WRAP_MODE])

        # set wrap_mode to 1 to leave instrument with wrap mode enabled
        new_params = {
            Parameter.WRAP_MODE : 1,
            Parameter.NUMBER_SAMPLES_PER_BURST : 10,
            Parameter.MEASUREMENT_INTERVAL : 600
        }
        
        # Set parameter and verify.
        reply = self.driver_client.cmd_dvr('set_resource', new_params)
        
        reply = self.driver_client.cmd_dvr('get_resource', [Parameter.WRAP_MODE, Parameter.NUMBER_SAMPLES_PER_BURST, Parameter.MEASUREMENT_INTERVAL])
        self.assertEqual(new_params, reply)
        
    def test_instrument_acquire_sample(self):
        """
        Test acquire sample command and events.
        """

        self.put_driver_in_command_mode()

        # command the instrument to auto-sample mode.
        self.driver_client.cmd_dvr('execute_resource', ProtocolEvent.ACQUIRE_SAMPLE)

        # wait for some samples to be generated
        gevent.sleep(120)

        # Verify we received at least 4 samples.
        sample_events = [evt for evt in self.events if evt['type']==DriverAsyncEvent.SAMPLE]
        log.debug('test_instrument_start_stop_autosample: # 0f samples = %d' %len(sample_events))
        #log.debug('samples=%s' %sample_events)
        self.assertTrue(len(sample_events) >= 4)

    def test_instrument_start_stop_autosample(self):
        """
        @brief Test for putting instrument in 'auto-sample' state
        """
        self.put_driver_in_command_mode()

        # command the instrument to auto-sample mode.
        self.driver_client.cmd_dvr('execute_resource', ProtocolEvent.START_AUTOSAMPLE)

        self.check_state(ProtocolState.AUTOSAMPLE)
           
        # re-initialize the driver and re-discover instrument state (should be in autosample)
        # Transition driver to disconnected.
        self.driver_client.cmd_dvr('disconnect')

        # Test the driver is disconnected.
        self.check_state(DriverConnectionState.DISCONNECTED)

        # Transition driver to unconfigured.
        self.driver_client.cmd_dvr('initialize')
    
        # Test the driver is unconfigured.
        self.check_state(DriverConnectionState.UNCONFIGURED)

        # Configure driver and transition to disconnected.
        self.driver_client.cmd_dvr('configure', self.port_agent_comm_config())

        # Test that the driver is in state disconnected.
        self.check_state(DriverConnectionState.DISCONNECTED)

        # Setup the protocol state machine and the connection to port agent.
        self.driver_client.cmd_dvr('connect')

        # Test that the driver protocol is in state unknown.
        self.check_state(ProtocolState.UNKNOWN)

        # Discover what state the instrument is in and set the protocol state accordingly.
        self.driver_client.cmd_dvr('discover_state')

        self.check_state(ProtocolState.AUTOSAMPLE)

        # wait for some samples to be generated
        gevent.sleep(200)

        # Verify we received at least 4 samples.
        sample_events = [evt for evt in self.events if evt['type']==DriverAsyncEvent.SAMPLE]
        log.debug('test_instrument_start_stop_autosample: # 0f samples = %d' %len(sample_events))
        #log.debug('samples=%s' %sample_events)
        self.assertTrue(len(sample_events) >= 4)

        # stop autosample and return to command mode
        self.driver_client.cmd_dvr('execute_resource', ProtocolEvent.STOP_AUTOSAMPLE)
                
        self.check_state(ProtocolState.COMMAND)
                        
    def test_capabilities(self):
        """
        Test get_resource_capaibilties in command state and autosample state;
        should be different in each.
        """
        
        command_capabilities = ['EXPORTED_INSTRUMENT_CMD_READ_ID', 
                                'EXPORTED_INSTRUMENT_CMD_GET_HW_CONFIGURATION', 
                                'DRIVER_EVENT_SET', 
                                'DRIVER_EVENT_GET', 
                                'EXPORTED_INSTRUMENT_CMD_READ_CLOCK', 
                                'EXPORTED_INSTRUMENT_CMD_GET_HEAD_CONFIGURATION', 
                                'EXPORTED_INSTRUMENT_CMD_POWER_DOWN', 
                                'EXPORTED_INSTRUMENT_CMD_READ_MODE', 
                                'EXPORTED_INSTRUMENT_CMD_START_MEASUREMENT_AT_SPECIFIC_TIME', 
                                'EXPORTED_INSTRUMENT_CMD_READ_BATTERY_VOLTAGE', 
                                'EXPORTED_INSTRUMENT_CMD_START_MEASUREMENT_IMMEDIATE',
                                'EXPORTED_INSTRUMENT_CMD_SET_CONFIGURATION', 
                                'DRIVER_EVENT_START_AUTOSAMPLE',
                                'DRIVER_EVENT_ACQUIRE_SAMPLE',
                                'DRIVER_EVENT_CLOCK_SYNC']
        
        autosample_capabilities = ['DRIVER_EVENT_STOP_AUTOSAMPLE']
        
        params_list = params_dict.keys()
        """
        [
            Parameter.TRANSMIT_PULSE_LENGTH,
            Parameter.BLANKING_DISTANCE,
            Parameter.RECEIVE_LENGTH,
            Parameter.TIME_BETWEEN_PINGS,
            Parameter.TIME_BETWEEN_BURST_SEQUENCES, 
            Parameter.NUMBER_PINGS,
            Parameter.AVG_INTERVAL,
            Parameter.USER_NUMBER_BEAMS, 
            Parameter.TIMING_CONTROL_REGISTER,
            Parameter.POWER_CONTROL_REGISTER,
            Parameter.COMPASS_UPDATE_RATE,  
            Parameter.COORDINATE_SYSTEM,
            Parameter.NUMBER_BINS,
            Parameter.BIN_LENGTH,
            Parameter.MEASUREMENT_INTERVAL,
            Parameter.DEPLOYMENT_NAME,
            Parameter.WRAP_MODE,
            Parameter.CLOCK_DEPLOY,
            Parameter.DIAGNOSTIC_INTERVAL,
            Parameter.MODE,
            Parameter.ADJUSTMENT_SOUND_SPEED,
            Parameter.NUMBER_SAMPLES_DIAGNOSTIC,
            Parameter.NUMBER_BEAMS_CELL_DIAGNOSTIC,
            Parameter.NUMBER_PINGS_DIAGNOSTIC,
            Parameter.MODE_TEST,
            Parameter.ANALOG_INPUT_ADDR,
            Parameter.SW_VERSION,
            Parameter.VELOCITY_ADJ_TABLE,
            Parameter.COMMENTS,
            Parameter.WAVE_MEASUREMENT_MODE,
            Parameter.DYN_PERCENTAGE_POSITION,
            Parameter.WAVE_TRANSMIT_PULSE,
            Parameter.WAVE_BLANKING_DISTANCE,
            Parameter.WAVE_CELL_SIZE,
            Parameter.NUMBER_DIAG_SAMPLES,
            Parameter.ANALOG_OUTPUT_SCALE,
            Parameter.CORRELATION_THRESHOLD,
            Parameter.TRANSMIT_PULSE_LENGTH_SECOND_LAG,
            Parameter.QUAL_CONSTANTS,
            ]
        """
        
        self.put_driver_in_command_mode()

        # Get the capabilities of the driver.
        driver_capabilities = self.driver_client.cmd_dvr('get_resource_capabilities')
        log.debug("\nec=%s\ndc=%s" %(sorted(command_capabilities), sorted(driver_capabilities[0])))
        self.assertTrue(sorted(command_capabilities) == sorted(driver_capabilities[0]))
        #log.debug('dc=%s' %sorted(driver_capabilities[1]))
        #log.debug('pl=%s' %sorted(params_list))
        self.assertTrue(sorted(params_list) == sorted(driver_capabilities[1]))

        # Put the driver in autosample
        self.driver_client.cmd_dvr('execute_resource', ProtocolEvent.START_AUTOSAMPLE)

        self.check_state(ProtocolState.AUTOSAMPLE)

        # Get the capabilities of the driver.
        driver_capabilities = self.driver_client.cmd_dvr('get_resource_capabilities')
        log.debug('test_capabilities: autosample mode capabilities=%s' %driver_capabilities)
        self.assertTrue(autosample_capabilities == driver_capabilities[0])
               
    def test_errors(self):
        """
        Test response to erroneous commands and parameters.
        """
        
        # Test that the driver is in state unconfigured.
        self.check_state(DriverConnectionState.UNCONFIGURED)

        # Assert for an unknown driver command.
        with self.assertRaises(InstrumentCommandException):
            self.driver_client.cmd_dvr('bogus_command')

        # Assert for a known command, invalid state.
        with self.assertRaises(InstrumentStateException):
            self.driver_client.cmd_dvr('execute_resource', ProtocolEvent.ACQUIRE_SAMPLE)

        # Assert we forgot the comms parameter.
        with self.assertRaises(InstrumentParameterException):
            self.driver_client.cmd_dvr('configure')

        # Assert we send a bad config object (not a dict).
        with self.assertRaises(InstrumentParameterException):
            BOGUS_CONFIG = 'not a config dict'            
            self.driver_client.cmd_dvr('configure', BOGUS_CONFIG)
            
        # Assert we send a bad config object (missing addr value).
        with self.assertRaises(InstrumentParameterException):
            BOGUS_CONFIG = self.port_agent_comm_config().copy()
            BOGUS_CONFIG.pop('addr')
            self.driver_client.cmd_dvr('configure', BOGUS_CONFIG)

        # Assert we send a bad config object (bad addr value).
        with self.assertRaises(InstrumentParameterException):
            BOGUS_CONFIG = self.port_agent_comm_config().copy()
            BOGUS_CONFIG['addr'] = ''
            self.driver_client.cmd_dvr('configure', BOGUS_CONFIG)
        
        # Configure driver and transition to disconnected.
        self.driver_client.cmd_dvr('configure', self.port_agent_comm_config())

        # Test that the driver is in state disconnected.
        self.check_state(DriverConnectionState.DISCONNECTED)

        # Assert for a known command, invalid state.
        with self.assertRaises(InstrumentStateException):
            self.driver_client.cmd_dvr('execute_resource', ProtocolEvent.ACQUIRE_SAMPLE)

        self.driver_client.cmd_dvr('connect')
                
        # Test the driver is in unknown state.
        self.check_state(ProtocolState.UNKNOWN)

        # Assert for a known command, invalid state.
        with self.assertRaises(InstrumentStateException):
            self.driver_client.cmd_dvr('execute_resource', ProtocolEvent.ACQUIRE_SAMPLE)
                
        self.driver_client.cmd_dvr('discover_state')

        try:
            # Test that the driver protocol is in state command.
            self.check_state(ProtocolState.COMMAND)
        except:
            self.assertEqual(self.protocol_state, ProtocolState.AUTOSAMPLE)
            # Put the driver in command mode
            self.driver_client.cmd_dvr('execute_resource', ProtocolEvent.STOP_AUTOSAMPLE)
            # Test that the driver protocol is in state command.
            self.check_state(ProtocolState.COMMAND)

        # Assert for a known command, invalid state.
        with self.assertRaises(InstrumentStateException):
            self.driver_client.cmd_dvr('execute_resource', ProtocolEvent.STOP_AUTOSAMPLE)
        
        # Assert for a known command, invalid state.
        with self.assertRaises(InstrumentStateException):
            self.driver_client.cmd_dvr('connect')
        
        # Assert get fails without a parameter.
        with self.assertRaises(InstrumentParameterException):
            self.driver_client.cmd_dvr('get_resource')
            
        # Assert get fails with a bad parameter (not ALL or a list).
        with self.assertRaises(InstrumentParameterException):
            bogus_params = 'I am a bogus param list.'
            self.driver_client.cmd_dvr('get_resource', bogus_params)
            
        # Assert get fails with a bad parameter (not ALL or a list).
        with self.assertRaises(InstrumentParameterException):
            bogus_params = [
                'a bogus parameter name',
                Parameter.ADJUSTMENT_SOUND_SPEED
                ]
            self.driver_client.cmd_dvr('get_resource', bogus_params)        
        
        # Assert we cannot set a bogus parameter.
        with self.assertRaises(InstrumentParameterException):
            bogus_params = {
                'a bogus parameter name' : 'bogus value'
            }
            self.driver_client.cmd_dvr('set_resource', bogus_params)
            
        # Assert we cannot set a real parameter to a bogus value.
        with self.assertRaises(InstrumentParameterException):
            bogus_params = {
                Parameter.ADJUSTMENT_SOUND_SPEED : 'bogus value'
            }
            self.driver_client.cmd_dvr('set_resource', bogus_params)
        

###############################################################################
#                            QUALIFICATION TESTS                              #
# Device specific qualification tests are for                                 #
# testing device specific capabilities                                        #
###############################################################################
@attr('QUAL', group='mi')
class QualFromIDK(InstrumentDriverQualificationTestCase):
    
    def assert_execute_resource(self, command):
        """
        @brief send an execute_resource command and ensure no exceptions are raised
        """
        
        # send command to the instrument 
        cmd = AgentCommand(command=ResourceAgentEvent.EXECUTE_RESOURCE,
                           args=[command])
        try:            
            return self.instrument_agent_client.execute_agent(cmd)
        except:
            self.fail('assert_execute_resource: execute_resource command failed for %s' %command)

    def assert_resource_capabilities(self, capabilities):

        def sort_capabilities(caps_list):
            '''
            sort a return value into capability buckets.
            @return res_cmds, res_pars
            '''
            res_cmds = []
            res_pars = []

            if(not capabilities.get(AgentCapabilityType.RESOURCE_COMMAND)):
                capabilities[AgentCapabilityType.RESOURCE_COMMAND] = []
            if(not capabilities.get(AgentCapabilityType.RESOURCE_PARAMETER)):
                capabilities[AgentCapabilityType.RESOURCE_PARAMETER] = []

            res_cmds = [x.name for x in caps_list if x.cap_type==CapabilityType.RES_CMD]
            res_pars = [x.name for x in caps_list if x.cap_type==CapabilityType.RES_PAR]

            return res_cmds, res_pars

        retval = self.instrument_agent_client.get_capabilities()
        res_cmds, res_pars = sort_capabilities(retval)

        log.debug("Resource Commands: %s " % str(res_cmds))
        log.debug("Resource Parameters: %s " % str(res_pars))
        
        log.debug("Expected Resource Commands: %s " % str(capabilities.get(AgentCapabilityType.RESOURCE_COMMAND)))
        log.debug("Expected Resource Parameters: %s " % str(capabilities.get(AgentCapabilityType.RESOURCE_PARAMETER)))

        self.assertEqual(sorted(capabilities.get(AgentCapabilityType.RESOURCE_COMMAND)), sorted(res_cmds))
        self.assertEqual(sorted(capabilities.get(AgentCapabilityType.RESOURCE_PARAMETER)), sorted(res_pars))

    def get_parameter(self, name):
        '''
        get parameter, assumes we are in command mode.
        '''
        getParams = [ name ]

        result = self.instrument_agent_client.get_resource(getParams)

        return result[name]

    def assert_sample_polled(self, sampleDataAssert, sampleQueue, timeout = 10):
        """
        Test observatory polling function.

        Verifies the acquire_sample command.
        """
        # Set up all data subscriptions.  Stream names are defined
        # in the driver PACKET_CONFIG dictionary
        self.data_subscribers.start_data_subscribers()
        self.addCleanup(self.data_subscribers.stop_data_subscribers)

        self.assert_enter_command_mode()

        for stream in sampleQueue:
            # make sure there aren't any old samples in the data queues.
            self.data_subscribers.clear_sample_queue(stream)

        # Poll for a sample
        cmd = AgentCommand(command=DriverEvent.ACQUIRE_SAMPLE)
        self.instrument_agent_client.execute_resource(cmd, timeout=timeout)
    
        for stream in sampleQueue:
            # Watch the parsed data queue and return once a sample
            # has been read or the default timeout has been reached.
            samples = self.data_subscribers.get_samples(stream, 1, timeout = timeout)
            self.assertGreaterEqual(len(samples), 1)
            log.error("SAMPLE: %s" % samples)
    
            # Verify
            for sample in samples:
                sampleDataAssert(sample)

        self.assert_reset()
        self.doCleanups()

    def assert_sample_autosample(self, sampleDataAssert, sampleQueue, timeout = 10):
        """
        Test observatory autosample function.

        Verifies the autosample command.
        """
        # Set up all data subscriptions.  Stream names are defined
        # in the driver PACKET_CONFIG dictionary
        self.data_subscribers.start_data_subscribers()
        self.addCleanup(self.data_subscribers.stop_data_subscribers)

        self.assert_enter_command_mode()

        for stream in sampleQueue:
            # make sure there aren't any old samples in the data queues.
            self.data_subscribers.clear_sample_queue(stream)

        # Begin streaming.
        self.assert_start_autosample()
    
        for stream in sampleQueue:
            # Watch the parsed data queue and return once a sample
            # has been read or the default timeout has been reached.
            samples = self.data_subscribers.get_samples(stream, 1, timeout = timeout)
            self.assertGreaterEqual(len(samples), 1)
            log.error("SAMPLE: %s" % samples)
    
            # Verify
            for sample in samples:
                sampleDataAssert(sample)

        # Halt streaming.
        self.assert_stop_autosample()

    def assertSampleDataParticle(self, sample):
        log.debug('assertSampleDataParticle: sample=%s' %sample)
        self.assertTrue(sample[DataParticleKey.PKT_FORMAT_ID],
            DataParticleValue.JSON_DATA)
        self.assertTrue(sample[DataParticleKey.PKT_VERSION], 1)
        self.assertTrue(isinstance(sample[DataParticleKey.VALUES],
            list))
        self.assertTrue(isinstance(sample.get(DataParticleKey.DRIVER_TIMESTAMP), float))
        self.assertTrue(sample.get(DataParticleKey.PREFERRED_TIMESTAMP))
        
        values = sample['values']
        value_ids = []
        for value in values:
            value_ids.append(value['value_id'])
        if sample[DataParticleKey.STREAM_NAME] == DataParticleType.VELOCITY:
            log.debug('assertSampleDataParticle: VectorVelocityDataParticle detected')
            self.assertEqual(sorted(value_ids), sorted(VectorVelocityDataParticleKey.list()))
            for value in values:
                self.assertTrue(isinstance(value['value'], int))
        elif sample[DataParticleKey.STREAM_NAME] == DataParticleType.VELOCITY_HEADER:
            log.debug('assertSampleDataParticle: VectorVelocityHeaderDataParticle detected')
            self.assertEqual(sorted(value_ids), sorted(VectorVelocityHeaderDataParticleKey.list()))
            for value in values:
                if value['value_id'] == VectorVelocityHeaderDataParticleKey.TIMESTAMP:
                    self.assertTrue(isinstance(value['value'], str))
                else:
                    self.assertTrue(isinstance(value['value'], int))
        elif sample[DataParticleKey.STREAM_NAME] == DataParticleType.SYSTEM:
            log.debug('assertSampleDataParticle: VectorSystemDataParticleKey detected')
            self.assertEqual(sorted(value_ids), sorted(VectorSystemDataParticleKey.list()))
            for value in values:
                if value['value_id'] == VectorSystemDataParticleKey.TIMESTAMP:
                    self.assertTrue(isinstance(value['value'], str))
                else:
                    self.assertTrue(isinstance(value['value'], int))
        elif sample[DataParticleKey.STREAM_NAME] == DataParticleType.PROBE_CHECK:
            log.debug('assertSampleDataParticle: VectorProbeCheckDataParticleKey detected')
            self.assertEqual(sorted(value_ids), sorted(VectorProbeCheckDataParticleKey.list()))
            for value in values:
                if value['value_id'] in (VectorProbeCheckDataParticleKey.BEAM_1_AMPLITUDES,
                                         VectorProbeCheckDataParticleKey.BEAM_2_AMPLITUDES,
                                         VectorProbeCheckDataParticleKey.BEAM_3_AMPLITUDES):
                    self.assertTrue(isinstance(value['value'], list))
                    for item in value['value']:
                        self.assertTrue(item, int)
                else:
                    self.assertTrue(isinstance(value['value'], int))
        else:
            self.fail('Unknown data particle')

    @unittest.skip("skip for automatic tests")
    def test_direct_access_telnet_mode_manually(self):
        """
        @brief This test manually tests that the Instrument Driver properly supports direct access to the physical instrument. (telnet mode)
        """
        self.assert_enter_command_mode()

        log.debug("test_direct_access_telnet_mode_manually: starting DA mode")
        # go direct access
        cmd = AgentCommand(command=ResourceAgentEvent.GO_DIRECT_ACCESS,
                           kwargs={#'session_type': DirectAccessTypes.telnet,
                                   'session_type':DirectAccessTypes.vsp,
                                   'session_timeout':600,
                                   'inactivity_timeout':600})
        retval = self.instrument_agent_client.execute_agent(cmd)
        log.warn("go_direct_access retval=" + str(retval.result))
        
        gevent.sleep(600)  # wait for manual telnet session to be run

    def test_direct_access_telnet_mode(self):
        """
        @brief This test manually tests that the Instrument Driver properly supports direct access to the physical instrument. (telnet mode)
        """
        self.assert_direct_access_start_telnet()
        self.assertTrue(self.tcp_client)

        self.tcp_client.send_data("K1W%!Q")
        self.tcp_client.expect("VECTOR")

        self.assert_direct_access_stop_telnet()

    def test_poll(self):
        '''
        poll for a single sample
        '''

        self.assert_sample_polled(self.assertSampleDataParticle,
                                  [DataParticleType.VELOCITY,
                                   DataParticleType.VELOCITY_HEADER,
                                   DataParticleType.SYSTEM],
                                  timeout = 100)

    def test_autosample(self):
        '''
        start and stop autosample and verify data particle
        '''
        self.assert_sample_autosample(self.assertSampleDataParticle,
                                  [DataParticleType.VELOCITY,
                                   DataParticleType.VELOCITY_HEADER,
                                   DataParticleType.SYSTEM,
                                   DataParticleType.PROBE_CHECK],
                                  timeout = 100)

    def test_get_set_parameters(self):
        '''
        verify that parameters can be get set properly
        '''
        self.assert_enter_command_mode()
        
        value_before_set = self.get_parameter(Parameter.BLANKING_DISTANCE)
        self.assert_set_parameter(Parameter.BLANKING_DISTANCE, 40)
        self.assert_set_parameter(Parameter.BLANKING_DISTANCE, value_before_set)

        value_before_set = self.get_parameter(Parameter.NUMBER_SAMPLES_PER_BURST)
        self.assert_set_parameter(Parameter.NUMBER_SAMPLES_PER_BURST, 60)
        self.assert_set_parameter(Parameter.NUMBER_SAMPLES_PER_BURST, value_before_set)

        self.assert_reset()
        
    def test_get_capabilities(self):
        """
        @brief Verify that the correct capabilities are returned from get_capabilities
        at various driver/agent states.
        """
        self.assert_enter_command_mode()

        ##################
        #  Command Mode
        ##################

        capabilities = {
            AgentCapabilityType.RESOURCE_COMMAND: [
                ProtocolEvent.SET, 
                ProtocolEvent.ACQUIRE_SAMPLE, 
                ProtocolEvent.GET, 
                ProtocolEvent.START_AUTOSAMPLE,
                ProtocolEvent.CLOCK_SYNC,
                ProtocolEvent.GET_HEAD_CONFIGURATION,
                ProtocolEvent.GET_HW_CONFIGURATION,
                ProtocolEvent.POWER_DOWN,
                ProtocolEvent.READ_BATTERY_VOLTAGE,
                ProtocolEvent.READ_CLOCK, 
                ProtocolEvent.READ_ID,
                ProtocolEvent.READ_FAT,
                ProtocolEvent.READ_MODE,
                ProtocolEvent.START_MEASUREMENT_AT_SPECIFIC_TIME,
                ProtocolEvent.START_MEASUREMENT_IMMEDIATE,
                ProtocolEvent.SET_CONFIGURATION
            ],
            AgentCapabilityType.RESOURCE_PARAMETER: [
                Parameter.TRANSMIT_PULSE_LENGTH,
                Parameter.BLANKING_DISTANCE,
                Parameter.RECEIVE_LENGTH,
                Parameter.TIME_BETWEEN_PINGS,
                Parameter.TIME_BETWEEN_BURST_SEQUENCES, 
                Parameter.NUMBER_PINGS,
                Parameter.AVG_INTERVAL,
                Parameter.USER_NUMBER_BEAMS, 
                Parameter.TIMING_CONTROL_REGISTER,
                Parameter.POWER_CONTROL_REGISTER,
                Parameter.COMPASS_UPDATE_RATE,  
                Parameter.COORDINATE_SYSTEM,
                Parameter.NUMBER_BINS,
                Parameter.BIN_LENGTH,
                Parameter.MEASUREMENT_INTERVAL,
                Parameter.DEPLOYMENT_NAME,
                Parameter.WRAP_MODE,
                Parameter.CLOCK_DEPLOY,
                Parameter.DIAGNOSTIC_INTERVAL,
                Parameter.MODE,
                Parameter.ADJUSTMENT_SOUND_SPEED,
                Parameter.NUMBER_SAMPLES_DIAGNOSTIC,
                Parameter.NUMBER_BEAMS_CELL_DIAGNOSTIC,
                Parameter.NUMBER_PINGS_DIAGNOSTIC,
                Parameter.MODE_TEST,
                Parameter.ANALOG_INPUT_ADDR,
                Parameter.SW_VERSION,
                Parameter.VELOCITY_ADJ_TABLE,
                Parameter.COMMENTS,
                Parameter.WAVE_MEASUREMENT_MODE,
                Parameter.DYN_PERCENTAGE_POSITION,
                Parameter.WAVE_TRANSMIT_PULSE,
                Parameter.WAVE_BLANKING_DISTANCE,
                Parameter.WAVE_CELL_SIZE,
                Parameter.NUMBER_DIAG_SAMPLES,
                Parameter.NUMBER_SAMPLES_PER_BURST,
                Parameter.ANALOG_OUTPUT_SCALE,
                Parameter.CORRELATION_THRESHOLD,
                Parameter.TRANSMIT_PULSE_LENGTH_SECOND_LAG,
                Parameter.QUAL_CONSTANTS
            ],
        }

        self.assert_resource_capabilities(capabilities)

        ##################
        #  Streaming Mode
        ##################

        capabilities[AgentCapabilityType.RESOURCE_COMMAND] =  [DriverEvent.STOP_AUTOSAMPLE]

        self.assert_start_autosample()
        self.assert_resource_capabilities(capabilities)
        self.assert_stop_autosample()

        #######################
        #  Uninitialized Mode
        #######################

        capabilities[AgentCapabilityType.RESOURCE_COMMAND] = []
        capabilities[AgentCapabilityType.RESOURCE_PARAMETER] = []

        self.assert_reset()
        self.assert_resource_capabilities(capabilities)

    def test_instrument_set_configuration(self):
        """
        @brief Test for setting instrument configuration
        """
        
        self.assert_enter_command_mode()
        
        # command the instrument to set the user configuration.
        cmd = AgentCommand(command=ResourceAgentEvent.EXECUTE_RESOURCE,
                           args=[ProtocolEvent.SET_CONFIGURATION],
                           kwargs={'user_configuration':base64.b64encode(user_config2())})
        try:
            self.instrument_agent_client.execute_agent(cmd)
            pass
        except:
            self.fail('test of set_configuration command failed')
        
    def test_instrument_clock_sync(self):
        """
        @brief Test for syncing clock
        """
        
        self.assert_enter_command_mode()
        
        # command the instrument to read the clock.
        response = self.assert_execute_resource(ProtocolEvent.READ_CLOCK)
        
        log.debug("read clock returned: %s", response)
        self.assertTrue(re.search(r'.*/.*/.*:.*:.*', response.result))

        # command the instrument to sync the clck.
        self.assert_execute_resource(ProtocolEvent.CLOCK_SYNC)

        # command the instrument to read the clock.
        response = self.assert_execute_resource(ProtocolEvent.READ_CLOCK)
        
        log.debug("read clock returned: %s", response)
        self.assertTrue(re.search(r'.*/.*/.*:.*:.*', response.result))
        
        # verify that the dates match 
        local_time = time.gmtime(time.mktime(time.localtime()))
        local_time_str = time.strftime("%d/%m/%Y %H:%M:%S", local_time)
        self.assertTrue(local_time_str[:12].upper() in response.result.upper())
        
        # verify that the times match closely
        instrument_time = time.strptime(response.result, '%d/%m/%Y %H:%M:%S')
        #log.debug("it=%s, lt=%s" %(instrument_time, local_time))
        it = datetime.datetime(*instrument_time[:6])
        lt = datetime.datetime(*local_time[:6])
        #log.debug("it=%s, lt=%s, lt-it=%s" %(it, lt, lt-it))
        if lt - it > datetime.timedelta(seconds = 5):
            self.fail("time delta too large after clock sync")      
