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
    eut = None
    chil = None
    pv = None
    result = script.RESULT_FAIL

    try:
        # Get the parameters for the test from the UI
        pf_start = ts.param_value('test.pf_start')
        pf_end = ts.param_value('test.pf_stop')
        steps = ts.param_value('test.pf_steps_per_side')
        sleep_time = ts.param_value('test.wait_time')

        # Initialize DER configuration
        eut = der.der_init(ts)
        eut.config()

        # Initialize CHIL environment, if necessary
        chil = hil.hil_init(ts)
        if chil is not None:
            chil.config()

        # PV simulator is initialized with test parameters and enabled
        pv = pvsim.pvsim_init(ts)
        pv.irradiance_set(800)
        pv.power_on()
        # Print information from the DER
        ts.log('---')
        info = eut.info()
        if info is not None:
            ts.log('DER info:')
            ts.log('  Manufacturer: %s' % (info.get('Manufacturer')))
            ts.log('  Model: %s' % (info.get('Model')))
            ts.log('  Options: %s' % (info.get('Options')))
            ts.log('  Version: %s' % (info.get('Version')))
            ts.log('  Serial Number: %s' % (info.get('SerialNumber')))
        else:
            ts.log_warning('DER info not supported')
        ts.log('---')
        fixed_pf = eut.fixed_pf()
        if fixed_pf is not None:
            ts.log('DER fixed_pf:')
            ts.log('  Ena: %s' % (fixed_pf.get('Ena')))
            ts.log('  PF: %s' % (fixed_pf.get('PF')))
            ts.log('  WinTms: %s' % (fixed_pf.get('WinTms')))
            ts.log('  RmpTms: %s' % (fixed_pf.get('RmpTms')))
            ts.log('  RvrtTms: %s' % (fixed_pf.get('RvrtTms')))
        else:
            ts.log_warning('DER fixed_pf not supported')
        ts.log('---')

        # Get EUT nameplate power
        eut_nameplate_power = eut.nameplate().get('WRtg')

        # disable volt/var, VW, FW
        eut.volt_var(params={'Ena': False})
        eut.volt_watt(params={'Ena': False})
        eut.freq_watt(params={'Ena': False})

        inv_power = eut.measurements().get('W')
        timeout = 120.
        if inv_power <= eut_nameplate_power / 10.:
            pv.irradiance_set(800)  # Perturb the pv slightly to start the inverter
            ts.sleep(3)
            eut.connect(params={'Conn': True})
        while inv_power <= eut_nameplate_power / 10. and timeout >= 0:
            ts.log('Inverter power is at %0.1f. Waiting %s more seconds or until EUT starts...' % (inv_power, timeout))
            ts.sleep(1)
            timeout -= 1
            inv_power = eut.measurements().get('W')
            if timeout == 0:
                result = script.RESULT_FAIL
                raise der.DERError('Inverter did not start.')



        # Create list of the power factor values to iterate over
        pf_values = list(np.linspace(pf_start, 1.0, num=steps)) + list(np.linspace(-1.0, pf_end, num=steps)[1:])
        # ts.log('Setting DER to the following PF values: %s' % pf_values)

        # Run the test for 3 different irradiance values
        for irr in [1000, 600, 300]:
            pv.irradiance_set(irr)  # Set irradiance of the PV simulator

            for pf in pf_values:
                # Send PF setting to the equipment under test (EUT)
                eut.fixed_pf(params={'Ena': True, 'PF': pf, 'WinTms': 0, 'RmpTms': 0, 'RvrtTms': 0})
                ts.log('Power Factor set to %0.3f. Sleeping for %0.2f seconds...' % (pf, sleep_time))
                ts.sleep(sleep_time)

        # Disable the PF function
        eut.fixed_pf(params={'Ena': False})
        ts.log('Power Factor Disabled')

        result = script.RESULT_COMPLETE

    except Exception, e:
        ts.log_error('Script failure: %s' % e)

    finally:
        if eut is not None:
            eut.fixed_pf(params={'Ena': False})
            eut.close()
        if chil is not None:
            chil.close()
        if pv is not None:
            pv.close()

    return result

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

# Expose parameters to the UI user
info.param_group('test', label='Test Parameters', glob=True)
info.param('test.pf_start', label='PF Start (pos)', default=0.85)
info.param('test.pf_stop', label='PF End (neg)', default=-0.85)
info.param('test.pf_steps_per_side', label='Steps per Quadrant', default=15)
info.param('test.wait_time', label='Sleep Time for Each PF Level', default=0.5)

# Expose the driver parameters through the abstraction layer
der.params(info)
pvsim.params(info)
hil.params(info)

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


