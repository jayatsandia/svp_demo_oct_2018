'''
Copyright (c) 2018, Sandia National Labs and SunSpec Alliance
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

# #!C:\Python27\python.exe

import sys
import os
import traceback
import math
import time
from svpelab import gridsim
from svpelab import pvsim
from svpelab import das
from svpelab import der
from svpelab import hil
import script
import numpy as np

def test_run():

    eut = None
    chil = None
    daq = None

    # result params
    result_params = {
        'plot.title': ts.name,
        'plot.x.title': 'Time (sec)',
        'plot.x.points': 'TIME',
        'plot.y.points': 'W_TARG, W_TOTAL, W_INV',
        'plot.y.title': 'EUT Power',
    }

    try:
        # Initialize DER configuration
        eut = der.der_init(ts)
        eut.config()

        # Initialize CHIL environment, if necessary
        chil = hil.hil_init(ts)
        if chil is not None:
            chil.config()

        # Initialize data acquisition with soft channels (sc) that include data that doesn't come from the DAQ
        sc_points = ['W_TARG', 'W_TOTAL', 'W_INV']
        daq = das.das_init(ts, sc_points=sc_points)
        ts.log('DAS device: %s' % daq.info())

        # Open result summary file - this will include a selection of DAQ data to evaluate performance of the EUT
        result_summary_filename = 'result_summary.csv'
        result_summary = open(ts.result_file_path(result_summary_filename), 'a+')  # Open .csv file
        ts.result_file(result_summary_filename)  # create result file in the GUI
        # Write result summary header
        result_summary.write('Test Name, Power Setting (%), Inverter-Reported Power (W), DAS Power (W)\n')

        # Get EUT nameplate power
        eut_nameplate_power = eut.nameplate().get('WRtg')

        for time_loop in range(10):
            daq.data_capture(True)  # Begin data capture for this power loop

            for power_limit_pct in [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]:
                daq.sc['W_TARG'] = eut_nameplate_power*(float(power_limit_pct)/100.)
                eut.limit_max_power(params={'Ena': True, 'WMaxPct': power_limit_pct})
                ts.log('EUT power set to %0.2f%%' % power_limit_pct)
                time.sleep(2)
                daq.sc['W_INV'] = eut.measurements().get('W')  # Get the inverter-measured power and save it.
                daq.data_sample()  # force a data capture point after the sleep and add this to the dataset
                daq_data = daq.data_capture_read()  # read the last data point dictionary from the daq object
                try:  # if 3 phase device add up the power from each phase
                    daq.sc['W_TOTAL'] = daq_data['AC_P_1'] + daq_data['AC_P_2'] + daq_data['AC_P_2']
                except Exception, e:  # if single phase device
                    daq.sc['W_TOTAL'] = daq_data['AC_P_1']
                # Record 1 set of power values for each power level setting
                result_summary.write('%s, %s, %s, %s\n' % (time_loop+1, power_limit_pct, daq.sc['W_INV'],
                                                           daq.sc['W_TOTAL']))

            daq.data_capture(False)  # Stop data capture
            ds = daq.data_capture_dataset()  # generate dataset from the daq data that was recorded
            filename = 'CurtailmentRun_%s.csv' % (str(time_loop+1))  # Pick name for the DAS data
            ds.to_csv(ts.result_file_path(filename))  # Convert data to .cvs file
            result_params['plot.title'] = testname  # update title for the excel plot for this dataset
            ts.result_file(filename, params=result_params)  # Add results info to .xml log, which will be used to plot
            ts.log('Saving data capture: %s' % filename)

    except Exception, e:
        raise 'Script failure: %s' % e

    finally:
        if eut is not None:
            eut.limit_max_power(params={'Ena': False})
            eut.close()
        if chil is not None:
            chil.close()
        if daq is not None:
            daq.close()

        # create result workbook
        excelfile = ts.config_name() + '.xlsx'
        rslt.result_workbook(excelfile, ts.results_dir(), ts.result_dir())
        ts.result_file(excelfile)

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


info = script.ScriptInfo(name=os.path.basename(__file__), run=run, version='1.0.2')

der.params(info)
hil.params(info)
das.params(info)

info.logo('sunspec.gif')

def script_info():
    
    return info


if __name__ == "__main__":
    # stand alone invocation
    config_file = None
    if len(sys.argv) > 1:
        config_file = sys.argv[1]

    test_script = script.TestScript(info=script_info(), config_file=config_file)

    run(test_script)
