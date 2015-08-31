Virtualization-Orchestration-layer
-------------------------------------

to run 

$ cd bin

$ python script.py pm_file image_file flavor_file

src
|
|
|-> VM_INFO (This file contains all the information of the vms formed from the machine)
|
|
|-> falvor_file (This file contains flavours to run the vm)
|
|
|-> image_file (This file contains the location of images)
|
|
|> main.py (This file contains the main orchestration code)
|
|
|-> pm_file (This file contains the location of all the physical machines)