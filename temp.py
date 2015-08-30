import os
import json
import libvirt

from json import JSONDecoder
from json import JSONEncoder
from flask import Flask , request , jsonify
from random import randint

app = Flask(__name__)
VM = {}
allocated = 0
pmid_allocated = 0

vmtypes = {"types":[{"tid":1,"cpu":1,"ram":512,"disk":1},{"tid":2,"cpu":2,"ram":1024,"disk":2},{"tid":3,"cpu":4,"ram": 2048,"disk": 3}]}
jsonString = JSONEncoder().encode({"types":[{"tid":1,"cpu":1,"ram":512,"disk":1},{"tid":2,"cpu":2,"ram":1024,"disk":2},{"tid":3,"cpu":4,"ram": 2048,"disk": 3}]})


@app.route('/')
def hello_world():
	conn = libvirt.open("qemu:///system")
	print conn.listDomainsID()  
	return 'Hello World!'


@app.route('/vm/create' , methods = ['GET'])
def create():
	conn = libvirt.open("qemu:///system")
	vm_name = request.args.get('name')
	instance_type = 0	                            #initialising vm_type
	instance_type = int(request.args.get('instance_type'))
	image_id = int(request.args.get('id'))	
	
	#json_data = open('info').readlines()
	#data = json.loads(json_data)
	cpu_required = vmtypes['types'][instance_type]['cpu']
	ram_required = vmtypes['types'][instance_type]['ram']
	dsk_required = vmtypes['types'][instance_type]['disk']
	uid = 0
	
	try:
		uid = max(conn.listDomainsID()) + 1
		uid = str(uid)
	except:
		uid = str(1)	
	

	##################CHECKING VALIDITY OF IMAGE_ID#########################
	found = 0
	imageFullPath = ""	
	fileopen  = open("image_file" , "r")
	imageInfo = fileopen.readlines()	
	for i in imageInfo:
		j = i.split()
		print j
		if int(image_id) == int(j[0]):
			imageFullPath = str(j[1])
			found = 1
			break
	if found == 0:
		return str(0)
	########################################################################


	print "PRINTING UID                       ",
	print uid

	xml = """<domain type='qemu' id='"""+uid+"""'>
			  <name>"""+vm_name+"""</name>
		  <memory unit='KiB'>"""+str(cpu_required)+"""</memory>
		  <vcpu placement='static'>1</vcpu>
		  <os>
		    <type arch='x86_64' machine='pc-0.11'>hvm</type>
		  </os>
		  <devices>
		    <disk type='file' device='cdrom'>
		      <source file='"""+  imageFullPath  +"""'/>
		      <target dev='hdc' bus='ide'/>
		    </disk>
		  </devices>
		</domain>
 		"""
	conn = libvirt.open("qemu:///system")			
	try:
		conn.defineXML(xml)
		dom = conn.lookupByName(vm_name)	
	except:
		return str(0)	
	try:
		VM[str(uid)] = {}
		VM[str(uid)]['name'] = str(vm_name)
		VM[str(uid)]['instance_type'] = instance_type
		####changing it now to call allocate func(but func to be changed)########VM[str(uid)]['pmid'] = 1		#for now it is hardcoded			
		
		pmid = int(allocatePm(int(cpu_required) , int(ram_required) , int(dsk_required)))		
		if pmid == 0:	
			return jsonify(status = int(0))
		VM[str(uid)]['pmid'] = int(pmid)
		try :		
			fileopen = open("vmidinfo","a")
			toFile = uid + "\t\t" + vm_name + "\t\t" + str(instance_type) + "\t\t" + str(pmid) + "\n"				
			fileopen.write(toFile)
			fileopen.close()
		except:
			print "unabele to write to file"
		##HERE CONNECTION HAS TO BE CHANGED BASED ON PMID		
		dom.create()
		return jsonify(vmid = uid)
	except:
		return str(0)
	return str(uid)






@app.route('/vm/query' , methods=['GET'])
def query():
	vmid = request.args.get('vmid')
	vmid = str(vmid)	
	conn = libvirt.open("qemu:///system")
	fileopen = open("vmidinfo" , 'ra')
	for vmscreated in fileopen:
		vminfo = vmscreated.split()
		if(vminfo[0] == vmid):
			return jsonify(vmid = vmid , name = vminfo[1] , instance_type=vminfo[2] ,pmid = vminfo[3])
	return str(0)





@app.route('/vm/destroy' , methods=['GET'])
def destroy():
	vmid = request.args.get('vmid')
	vmid = str(vmid)
	conn = libvirt.open("qemu:///system")
	fileopen = open("vmidinfo" , "r+")
	fileinfo = fileopen.readlines()
	#print fileinfo	
	fileopen.seek(0)
	try:
		vm_name = str('a')
		for i in fileinfo:
			j = i.split()
			print j
	
			if j[0] == vmid:
				print "****************"	
				vm_name = j[1]
			else:
				fileopen.write(i)	
		print vm_name		
		dom  = conn.lookupByName(vm_name)
		dom.destroy()
		conn.close()
		fileopen.truncate()
		fileopen.close()
		return jsonify(status = 1)
	except:
		conn.close()
		return jsonify(status = 0)
	



############THIS IS DONE BUT WRITE A SCRIPT TO CREATE INFO FILE OR DO NOT USE THAT FILE
@app.route('/vm/types')
def types():
	#vm_types_file = open("info" , "r")
	#val = json.loads(vm_types_file.read())
	#return jsonify(val)
	return jsonify(vmtypes)


#done
@app.route('/pm/list')
def list():
	#use a file for pmids also return the list of pmids from that file
	fileopen = open("pm_file" , "r")
	fileinfo = fileopen.readlines()
	L = []	
	for i in fileinfo:
		j = i.split()		
		L.append(int(j[0])) 	
	fileopen.close()	
	return jsonify( pmids = L)



#done
@app.route('/pm/listvms')
def getVmsfromid():
	pmid = request.args.get('pmid')
	pmid = str(pmid)
	fileopen = open("vmidinfo" , "r")
	vms_present = []	
	pms_file = open("pm_file" , "r")
	pms_info = pms_file.readlines()
	found = 0	
	for i in pms_info:
		j = i.split()
		if int(pmid)==int(j[0]):
			found = 1
			break
	if found==0:
		return str(0) 
	for i in fileopen:
		print i		
		curr_vm = i.split()
		if curr_vm[3] == pmid:
			vms_present.append(int(curr_vm[0]))
	return jsonify(vmids = vms_present)	




##WORKING FOR THIS PC , CHECK AFTER SSH

@app.route('/pm/query')					#for now i'm just printing info of my laptop
def getPmInfo():					#tobedone: ssh to all pms , make a list r, jsonify and return
	
	pmid   = request.args.get('pmid')					 	
	pm_cap = {}
	pm_fre = {}
	

	#################################FETCHING IP FROM GIVEN PMID#####################
	pm_ip = str(1)
	pms_file = open("pm_file" , "r")
	pms_info = pms_file.readlines()
	found = 0	
	for i in pms_info:
		j = i.split()
		if int(pmid)==int(j[0]):
			pm_ip = str(j[1])			
			found = 1
			break
	if found==0:
		return str(0) 
	#############################FETCHING IP DONE HERE###############################
	
	print pm_ip

	##############################HERE THE CONNECTION IS TO BE CHANGED AND THAT'S IT	
	conn = libvirt.open("qemu:///system")	
	pm_cpu = conn.getMaxVcpus(None)
	pm_mem = conn.getMemoryStats(0 , 0)
	pm_cap['cpu'] = int(pm_cpu)
	pm_cap['ram'] = int(pm_mem['total'])
	pm_fre['cpu'] = int(pm_cpu)
	pm_fre['ram'] = int(pm_mem['free'])
	########################disk taken li8
	fileopen = open("vmidinfo" , "r")
	vms_using= 0
	json_data = open('info').read()
	data = json.loads(json_data)
	for i in fileopen:
		j = i.split()
		if j[3] == pmid:
			vms_using = vms_using + 1
			pm_fre['cpu'] = pm_fre['cpu'] - 1   ##to be corrected
	return jsonify(pmid = int(pmid) ,  capacity = pm_cap , free = pm_fre , vms = int(vms_using))
	
	



#done
@app.route('/image/list')
def getImagesinfo():
	fileopen = open("image_file", "r")
	Images   = []
	temp = []
	for imageInfo in fileopen:
		fullpath = imageInfo.split()			
		print fullpath[0]
		iname    = {}		
		iname['id'] = int(fullpath[0])
		temp = fullpath[1].split('/')	
		iname['name'] = str(temp[len(temp)-1])
		Images.append(iname)
	return jsonify(images = Images)







def allocatePm(cpu , ram , disk):
	#here i have to write a loop which looks into all physical machines
	global pmallocated
	global allocated
	##(HIGH)DOUBT CAN I CONNECT ANY NUMBER OF TIMES 
	conn = libvirt.open("qemu:///system")	
	pm_cpu = conn.getMaxVcpus(None)
	pm_mem = conn.getMemoryStats(0 , 0)
	########################check here wheather cpu is automatically subtracted or we have to do that
	if int(pm_mem['free']) >= int(ram):
		if int(pm_cpu) >= int(cpu):
			pmid_allocated = 1			#has to be changed when for loop is used			
			allocated = 1
			return 1	#for now 1 later iterator		
	return 0			#0 means no PM found





















if __name__ == "__main__":
	conn = libvirt.open("qemu:///system")

	########################AS WE ARE ASKED TO ASSIGN UNIQUE PMIDS ########################
	fileopen = open("pm_file" , "r+")
	fileinfo = fileopen.readlines()
	fileopen.seek(0)
	pmid = 2			#pmid=1 for the localhost
	for i in fileinfo:
		t = i.split()
		if len(t) == 2:
			if int(t[0]) > pmid:
				pmid = int(t[0])+1
	for i in fileinfo:
		t = i.split()
		if len(t)==1:				
			pmid = pmid + 1			
			fileopen.write(str(pmid)+"\t\t"+i)			 		
		else:
			fileopen.write(i)	
	fileopen.truncate()
	fileopen.close()	
	###########################ASSIGINING UNIQUE PMIDS DONE HERE############################

	#######AS WE ARE ASKED TO ASSIGN UNIQUE IDS TO IMAGES########################

	fileopen = open("image_file" , "r+")
	fileinfo = fileopen.readlines()
	fileopen.seek(0)
	image_id = 1
	for i in fileinfo:
		t = i.split()
		if len(t)==2:
			if int(t[0]) > image_id:
				image_id = int(t[0]) + 1
	for i in fileinfo:
		t = i.split()
		if len(t)==1:				
			fileopen.write(str(image_id)+"\t\t"+i)
			image_id = image_id + 1 		
		else:
			fileopen.write(i)	
	fileopen.truncate()
	fileopen.close()
	
	########################ASSIGNING UNIQUE IDS TO IMAGES DONE ###################

	app.run(debug = True)


















