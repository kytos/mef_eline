#########
Changelog
#########
All notable changes to the MEF_ELine NApp will be documented in this file.

[2.3.2] - 2019-06-12
********************************
Added
=====
 - Added EVC status check when deploying using schedule.
 - Serialize circuit scheduler for storehouse.
 - Fix VLAN availability on interfaces after using them.
 - Documentation about delete method.

Changed
=======
  - Updated coments on methods.
  - Updated OpenApi Models description and documentation.

Deprecated
==========

Removed
=======
  - Removed dependencies.

Fixed
=====
  - Linter issues

Security
========

[2.3.1] - 2019-03-15
********************

Added
=====
 - Scrutinizer running after every push to GitHub repository.
 - Linter checking all python code.

Fixed
=====
 - Fixed link up/down events from kytos/topology (#99 and #100).
 - Load VLANs from storehouse (#101).
 - Check path status using kytos/topology (#102).
 - Fixed tests to mock call to get links from kytos/topology (#118).

[2.3.0] - 2018-12-14
********************

Added
=====
 - Added more API documentation.
 - Added EVC flow removal based on cookies.
 - Added EVC deletion API method.

Fixed
=====
 - Fixed circuit not being deployed.
 - Fixed `current_path` changes not being saved on storehouse (#85).
 - Fixed storehouse always creating a new box (#91).
 - Fixed handling of link up/down events.

[2.2.2] - 2018-10-15
********************

Fixed
=====
 - Fixed error when creating a circuit with scheduling and without `start_date`
   (#79 and #80)

[2.2.1] - 2018-09-06
********************
Added
=====
- Added endpoint to allow update circuit informations.
- Added structure to support ci integration: unittests, linter, tox and
  scrutinizer.
- Added some tests for the class already created.
- Added some LinkProtection features:
  - Added method to handle when links goes up or end_maintenance.
  - Added method to handle when links goes down or under_maintenance.
  - When primary_path and backup_path goes down or under_maintenance and
    `dynamic_backup_path` is setted as True a dynamic path is choosed using the
    PathFinder NApp when the primary and backup path is both down or not
    setted.
  - When the primary_path is down and backup_path exists and is UP the circuit
    will change from primary_path to backup_path.
  - When the primary_path change from DOWN to UP the circuits will change to
    the primary_path.
  - When the circuit is disabled the circuit will not be deployed.
  - Added method to looking for links affected was created using the python
    `set` class to be more fast to find the links affected.

Changed
=======
- Change deploy to use primary_path, backup_path or a dynamic_path.
- Improved the Schedule to use advanced python scheduler (APScheduler) library.
Thanks @ajoaoff for recommends this library.
- The attribute circuit_scheduler in the EVC class should have some instances
of CircuitScheduler, this instances will have the information about the
scheduler informations.

Fixed
=====
- Fixed the create circuit method when sending a invalid request
- Fixed some linter warnings.

[2.2.0] - 2018-06-15
********************
Added
=====
- Added EVC class to represent a circuit.
- Added Schedule class to schedule the circuit deploy.
- Added persistence with the NApp kytos/storehouse.

Changed
=======
- Refactore main.py and models.py

Fixed
=====
- Removed duplicated key in openapi.yml

[2.1.0] - 2018-04-20
********************
Added
=====
- Add Schedule class
- Add Mef-Eline component

Changed
=======
- Update openapi.yml
- Update README.rst

[2.0.0] - 2018-03-09
********************
Added
=====
- New /evc endpoint.
- Future endpoint URLs.
- EPL and EVPL support, with VLANs in both endpoints.

Changed
=======
- Method to install flows to the switches.
- List of links now represented by Link objects.

Removed
=======
- Old /circuit endpoints.
