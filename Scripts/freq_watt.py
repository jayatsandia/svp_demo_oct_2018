'''
Copyright (c) 2016, Sandia National Labs and SunSpec Alliance
All rights reserved.

Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the following conditions are met:

Redistributions of source code must retain the above copyright notice, this
list of conditions and the following disclaimer.

Redistributions in binary form must reproduce the above copyright notice, this
list of conditions and the following disclaimer in the documentation and/or
other materials provided with the distribution.

Neither the names of the Sandia National Labs and SunSpec Alliance nor the names of its
contributors may be used to endorse or promote products derived from
this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR
ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

Written by Sandia National Laboratories, Loggerware, and SunSpec Alliance
Questions can be directed to Jay Johnson (jjohns2@sandia.gov)
'''

#!C:\Python27\python.exe

import sys
import os
import traceback
from svpelab import das
from svpelab import der
from svpelab import pvsim
from svpelab import hil
import script
import numpy as np

def test_run():

    # Initialize DER configuration
    eut = der.der_init(ts)
    eut.config()

    # Initialize CHIL environment, if necessary
    chil = hil.hil_init(ts)
    if chil is not None:
        chil.config()

    # PV simulator is initialized with test parameters and enabled
    pv = pvsim.pvsim_init(ts)
    pv.irradiance_set(1000)
    pv.power_on()

    # grid simulator is initialized with test parameters and enabled
    grid = gridsim.gridsim_init(ts)

    fw_mode = 'Pointwise'
    if fw_mode == 'Parameters':
        eut.freq_watt_param(params={'HysEna': False, 'HzStr': 50.2,
                                    'HzStop': 51.5, 'WGra': 140.})
    else:  # Pointwise
        eut.freq_watt(params={'ActCrv': 1})
        f_points = [50, 50.2, 51.5, 53]
        p_points = [100, 100, 0, 0]
        parameters = {'hz': f_points, 'w': p_points}
        # ts.log_debug(parameters)
        eut.freq_watt_curve(id=1, params=parameters)
        eut.freq_watt(params={'Ena': True})
        ts.log_debug(eut.freq_watt())

    # Create list of frequencies to iterate over
    freq_values = list(np.linspace(49.5, 53, num=50))
    sleep_time = 0.5
    for freq in freq_values:
        grid.freq(freq)  # set grid frequency
        ts.log('      f = %0.3f Hz. Sleeping for %0.2f seconds...' % (freq, sleep_time))
        ts.sleep(sleep_time)

    # Disable the FW function
    eut.freq_watt(params={'Ena': False})
    ts.log('FW Disabled')

    # Close the connection to the CHIL
    if chil is not None:
        chil.close()

    return script.RESULT_COMPLETE

def run(test_script):

    try:
        global ts
        ts = test_script
        rc = 0
        result = script.RESULT_COMPLETE

        ts.log_debug('')
        ts.log_debug('**************  Starting %s  **************' % (ts.config_name()))
        ts.log_debug('Script: %s %s' % (ts.name, ts.info.version))
        ts.log_active_params()

        result = test_run()

        ts.result(result)
        if result == script.RESULT_FAIL:
            rc = 1

    except Exception, e:
        ts.log_error('Test script exception: %s' % traceback.format_exc())
        rc = 1

    sys.exit(rc)

info = script.ScriptInfo(name=os.path.basename(__file__), run=run, version='1.0.0')

# Expose the driver parameters through the abstraction layer
der.params(info)
pvsim.params(info)
hil.params(info)
gridsim.params(info)

# Add a logo to the SVP
info.logo('sunspec.gif')

def script_info():
    
    return info


if __name__ == "__main__":

    # stand alone invocation
    config_file = None
    if len(sys.argv) > 1:
        config_file = sys.argv[1]

    params = None

    test_script = script.Script(info=script_info(), config_file=config_file, params=params)

    run(test_script)


