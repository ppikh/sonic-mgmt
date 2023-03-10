# DPU "show platform temperature" test plan

* [Overview](#Overview)
   * [Scope](#Scope)
   * [Testbed](#Testbed)
   * [Setup configuration](#Setup%20configuration)
* [Test](#Test)
* [Test cases](#Test%20cases)
* [TODO](#TODO)
* [Open questions](#Open%20questions)

## Overview
The purpose is to test functionality of temperature sensors on the SONIC DPU device.

### Scope
The test is targeting a running SONIC DPU system. The purpose of the test is to test output of command "show platform temperature" and sensors functionality on DPU device.

### Testbed
The test will run on the DPU testbeds.

### Setup configuration
If device is BF3 - before run test will be installed application "stress" using: "apt update && apt install -y stress"

## Test

## Test cases

### Test case # 1 – test_dpu_show_platform_temperature
#### Test objective
Verify DPU "show platform temperature" output
#### Test steps
* Do command "show platform temperature"
* Verify that all expected sensors available:
  * BF2: ASIC, DDR0_0, DDR0_1, DDR1_0, DDR1_1, SFP0, SFP1
  * BF3: CPU, DDR, SFP0, SFP1
<<<<<<< HEAD
* Verify values for sensors(BF2 - validate only ASIC):
  * ASIC/CPU:
    * Temperature - float value in range "Crit Low TH" - "Crit High TH"
    * High TH - float value 95.0
    * Low TH - float value 5.0
    * Crit High TH - float value 100.0
=======
* Verify values for sensors:
  * ASIC/CPU:
    * Temperature - float value in range 5.0-105.0
    * High TH - float value 95.0
    * Low TH - float value 5.0
    * Crit High TH - float value 105.0
>>>>>>> afaab6bbd9aaf674f4ddde9e3aed2c229c9646ab
    * Crit Low TH - float value 5.0
    * Warning - string "False"
    * Timestamp - string, timestamp in format: 20230307 12:11:48
  * DDR(for BF3):
    * Temperature - float value in range 0.0-100.0  # not specified in HLD
<<<<<<< HEAD
    * High TH - float value 95.0
    * Low TH - float value 5.0
    * Crit High TH - float value 100.0
    * Crit Low TH - float value 5.0
=======
    * High TH - string, "N/A"
    * Low TH - string, "N/A"
    * Crit High TH - string, "N/A"
    * Crit Low TH - string, "N/A"
>>>>>>> afaab6bbd9aaf674f4ddde9e3aed2c229c9646ab
    * Warning - string "False"
    * Timestamp - string, timestamp in format: 20230307 12:11:48
  * DDRX_X(for BF2):
    * Temperature - string, "N/A"
    * High TH - string, "N/A"
    * Low TH - string, "N/A"
    * Crit High TH - string, "N/A"
    * Crit Low TH - string, "N/A"
    * Warning - string "False"
    * Timestamp - string, timestamp in format: 20230307 12:11:48
  * SFP:
    * Temperature - for BF2 - string "N/A", for BF3 - float value in range 0.0-100.0  # not specified in HLD
    * High TH - string, "N/A"
    * Low TH - string, "N/A"
    * Crit High TH - string, "N/A"
    * Crit Low TH - string, "N/A"
    * Warning - string "False"
    * Timestamp - string, timestamp in format: 20230307 12:11:48

#### All logic below will be executed if device is BF3:
* Store CPU current temperature value
* Run stress test for 2 min which will use CPU(all cores), example: stress --cpu 8 --timeout 120s
<<<<<<< HEAD
* Get temperature of CPU from output of "show platform temperature" - check that temperature higher than before test at lest +1 degree
* Wait 30 sec
* Get temperature of CPU from output of "show platform temperature" - check that temperature less than after stress test at lest -1 degree
=======
* Get temperature of CPU from output of "show platform temperature" - check that temperature higher than before test
* Wait 30 sec
* Get temperature of CPU from output of "show platform temperature" - check that temperature less than after stress test
>>>>>>> afaab6bbd9aaf674f4ddde9e3aed2c229c9646ab

## TODO

## Open questions
