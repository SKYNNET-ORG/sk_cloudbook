# CLOUDOOK DEPLOYER

The Cloudbook deployer component runs only in one machine of the project and it is in charge of assigning DUs to the active agents.


### Requirements

* Python 3.X
* Windows or Ubuntu 18 (may work on other OS but only designed and tested for these ones)
* Python modules (you can install them with pip3):
	- requests


### How to use

* Launching the deployer (**cloudbook_deployer**):
	The deployer can be launch from the command line with the folloing syntax:
	`cloudbook_deployer.py -project_folder <project_folder> [-s <period>] [-fast_start]`

	Example: `cloudbook_deployer.py -project_folder <project_folder> -s 40`

	* Where the options are:
		**-project_folder <project_folder>**    The name of the project for which the deployer will be run.
		**[-s <period>]**                       The deployer will be run with surveillance mode, with the indicated period (in seconds).
		**[-fast_start]**                       The deployer will be run without waiting at the start, assumming that all the agent_grant files have been recently written.


* Launching the user program (**cloudbook_run**):
	The user program can be launch from the command line with the folloing syntax:
	`cloudbook_run.py -project_folder <project_folder>`

	Example: `cloudbook_run.py -project_folder <project_folder>`

	* Where the options are:
		**-project_folder <project_folder>**    The name of the project for with the user program will be run with cloudbook.


_Note: the order of the options is not relevant in any of the programs._

_Note 2: remember that the scripts must be run with python3, then you should use the full syntax `python3 <command>` in Unix and `py -3 <command>` in Windows._
