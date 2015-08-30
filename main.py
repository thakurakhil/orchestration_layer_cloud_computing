from flask import Flask, request, session, url_for, redirect, \
     render_template, abort, g, flash, _app_ctx_stack, jsonify
import json
import libvirt
import os,sys
import xml.etree.ElementTree as ET
from uuid import uuid4
import subprocess

# configuration
app = Flask(__name__)

#variables
machine_list = []
img_details_list = []
VMTypesDescription = {}
img_path_list = []

machines_list = []
flag = 0
selected_pm = ""
vmid_selectedpm_dict = {}
machines_count=1
pmid = {}
VM = {}
VM_ID_LIST = []
VM_NAME = []

def get_machines(filename):
    f = open(sys.argv[1], "r")
    global machines_list
    global machines_count
    coun = 1
    machines_list = []
    for i in f.readlines():
        i = i.strip('\n')
        machines_list.append(i.strip("\r"))
        pmid[i.strip("\r")] = coun
        coun = coun + 1

    machines_count = len(machines_list)

def get_images(filename):	
	imgfile = open(filename)
	count=1
	for line in imgfile.readlines():
		line = line.strip('\n')
		if line:
			img1 = line.split("@")
			img2 = img1[1].split(":")
			img = []
			img.append(img1[0])
			img.append(img2[0])
			img.append(img2[1])
			img_path_list.append(img)
			img = []
			img.append(count)
			img.append(img2[1].split('/')[-1])
			img_details_list.append(img)
			count=count+1

def jsonifyTypes(Filename):
    global VMTypesDescription
    VMTypeJsonFile=open(Filename)
    VMLines=VMTypeJsonFile.readlines()
    vMDesc=unicode(''.join(  map(lambda lin: lin.strip(),VMLines) )  )
    VMTypesDescription=json.loads(vMDesc)


def get_vm_types(tid=None):

    f = open(vm_types_filename, "r")
    val = json.loads(f.read())[u'types']
    if tid!=None:
        for i in val:
            if i[u'tid'] == tid:
                return i
    else:
        return val
    return 0

def Scheduler(cpu, ram, disk):
    
    global flag
    for i in range(len(machines_list)):
        if i == flag:
            flag = flag + 1
            pm_ram = (subprocess.check_output(" ssh " + machines_list[i] + "  free -m | grep 'Mem:' | awk '{ print $4 }'" , shell=True))
            pm_cpu = int(subprocess.check_output(" ssh " + machines_list[i] + " nproc" , shell=True))
            pm_ram = pm_ram.strip("\n")
            if int(pm_ram) >= int(ram):
                if int(pm_cpu) >= int(cpu):
                    return machines_list[i]
            if i == len(machines_list)-1:
                i = 0
                falg = 0



@app.route('/server/vm/create/' , methods = ['GET'])
def vm_create():
    args = request.args
    VM_name = str(args['name'])
    VM_type_id = int(args['instance_type'])
    VM_details = get_vm_types(VM_type_id)

    vm_cpu = VM_details['cpu']
    vm_ram = VM_details['ram']
    vm_disk = VM_details['disk']

    # Schedular
    global selected_pm
    selected_pm = Scheduler(vm_cpu, vm_ram, vm_disk)
    #print selected_pm
    user_name = selected_pm.split("@")[0]
    #print list(user_name)
    #send_image(selected_pm, vm_image_path)
    global vm_image_path
    for vm in img_path_list:
        if vm[0] == user_name and vm[1] == selected_pm.split("@")[1]:
            vm_image_name = vm[2].split("/")[-1].strip("\r")
            vm_image_path = vm[2].split(":")[0].strip("\r")
        
    global VM_ID_LIST
    global VM
    global vmid_selectedpm_dict
    if len(VM_ID_LIST)==0:
        i = 1
    else:
        i = int(VM_ID_LIST[-1])+1
    vmid = i
    VM_ID_LIST.append(vmid)
    vmid_selectedpm_dict[str(vmid)] = selected_pm
    VM[str(vmid)] = {}
    VM[str(vmid)]['Name'] = VM_name
    VM[str(vmid)]['PM'] = selected_pm
    VM[str(vmid)]['instance_type'] = VM_type_id
    VM[str(vmid)]['pmid'] = pmid[selected_pm]
    #imagePath = vm['name'].split(":")[0].strip("\r")
    xml = """
    <domain type='qemu' id='%s'>
    <name>%s</name>
	<memory>%s</memory>
	<currentMemory>131072</currentMemory>
	<vcpu>%s</vcpu>
    <os>
    <type>hvm</type>
    <boot dev='hd'/>
    </os>
    <devices>
    <disk type='file' device='disk'>
    <source file='%s' />
    <target dev='hda'/>
    </disk>
    <interface type='network'>
    <source network='default'/>
    </interface>
    
    </devices>
    </domain>
    """ % (i, VM_name, str(int(vm_ram)*1024), str(vm_cpu), vm_image_path)
#img_path_list[]
#str(imagePath)
    try:
        conn = libvirt.open("qemu+ssh://"+vmid_selectedpm_dict[str(vmid)]+"/system")
        conn.defineXML(xml)
        dom = conn.lookupByName(VM_name)
        dom.create()
        result = "{\n%s\n}" % str(vmid)
        conn.close()
        #return result
        return jsonify(vmid=str(vmid))
    except Exception,e: 
    	print str(e)
        #conn.close()
        #return str(0)
        res=str(vmid)
        return jsonify(status=0,stats=vmid_selectedpm_dict[str(vmid)], xml=xml,result=res)


@app.route('/server/vm/query/' , methods = ['GET'])
def vm_query():

    args = request.args
    VM_id = str(args['vmid'])
    return jsonify(vmid=VM_id, name=VM[str(VM_id)]['Name'], instance_type=VM[str(VM_id)]['instance_type'], pmid=VM[str(VM_id)]['pmid'])

@app.route('/server/vm/destroy/' , methods = ['GET'])
def vm_destroy():
    try:
	args = request.args
	VM_id = str(args['vmid'])
	user= VM[str(VM_id)]['PM'].strip("@")[0]
	ip= VM[str(VM_id)]['PM'].strip("@")[1]
	print user	
	connect = libvirt.open("qemu+ssh://"+vmid_selectedpm_dict[str(VM_id)]+"/system")
	req = connect.lookupByName(VM[str(VM_id)]['Name'])
	if req.isActive():
	    req.destroy()
	req.undefine()
	del VM[str(VM_id)]
	return jsonify(status=1)
    except Exception,e: 
    	print str(e)
	return jsonify(status=0)

@app.route('/server/vm/types', methods=['GET'])
def vm_types():
    return jsonify(VMTypesDescription)

@app.route('/server/pm/list', methods=['GET'])
def list_pms():
	return jsonify(pmids=pmid.values())

@app.route('/server/pm/pmid/listvms', methods=['GET'])
def list_vms():
    return jsonify(vmids=VM.keys())

@app.route('/server/pm/pmid', methods=['GET'])
def pm_query():
    args = request.args
    PM_id = str(args['pmid'])
    PM_ram = (subprocess.check_output(" ssh " + machines_list[int(PM_id) - 1] + "  free -m | grep 'Mem:' | awk '{ print $4 }'" , shell=True))
    PM_ram_total = (subprocess.check_output(" ssh " + machines_list[int(PM_id) - 1] + "  free -m | grep 'Mem:' | awk '{ print $2 }'" , shell=True))
    PM_cpu = int(subprocess.check_output(" ssh " + machines_list[int(PM_id) - 1] + " nproc" , shell=True))
    PM_ram = PM_ram.strip("\n")
    PM_ram_total = PM_ram_total.strip("\n")
    capacity = {'cpu':PM_cpu, 'ram':PM_ram_total, 'disk': 1}
    free = {'cpu': PM_cpu, 'ram': PM_ram, 'disk': 1}
    vm_count = 0;
    for i in VM.values():
    	if(str(i['pmid']) == PM_id):
    		vm_count = vm_count + 1
    return jsonify(pmid=PM_id, capacity=capacity, free=free, vms=vm_count)

@app.route('/server/image/list', methods=['GET'])
def list_images():
    im = []
    for i in img_details_list:
	im.append({'id':i[0], 'name':i[1]})
    return jsonify(images=im)


if __name__ == '__main__':
    global vm_types_filename
    vm_types_filename = sys.argv[3]
    jsonifyTypes(vm_types_filename)
    get_machines(sys.argv[1])
    get_images(sys.argv[2])
    app.run(debug = True)
