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
selected_pm = ""
machines_count=1
pmid = {}
VM = {}

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
            		img.append(count)
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

def send_image(pm, image_path):
    
    image_path = image_path.strip("\r")
    if pm == image_path.split(":")[0]:
        return
    os.system("ssh " + pm + " rm /home/"+pm.split("@")[0]+"/"+image_path.split("/")[-1])
    bash_command = "scp " + image_path + " " + pm + ":/home/" + pm.split("@")[0] + "/"
    #print bash_command
    os.system(bash_command)

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
    
    for i in range(len(machines_list)):
        pm_ram = (subprocess.check_output(" ssh " + machines_list[i] + "  free -m | grep 'Mem:' | awk '{ print $4 }'" , shell=True))
        pm_cpu = int(subprocess.check_output(" ssh " + machines_list[i] + " nproc" , shell=True))
        pm_ram = pm_ram.strip("\n")
        pm_disk = int(subprocess.check_output(" ssh " + machines_list[i] + " df --total -TH --exclude-type=tmpfs | awk '{print $5}' | tail -n 1 | cut -b -2" , shell=True))
        if int(pm_ram) >= int(ram):
            if int(pm_cpu) >= int(cpu):
                if int(pm_disk) >= int(disk):
                    return machines_list[i]
        if i == len(machines_list)-1:
            i = 0


@app.route('/')
def hello():
    return jsonify(status = "Hello world!")

@app.route('/vm/create/' , methods = ['GET'])
def vm_create():
    args = request.args
    VM_name = str(args['name'])
    VM_type_id = int(args['instance_type'])
    VM_image_type = int(args['image_id'])
    VM_details = get_vm_types(VM_type_id)

    vm_cpu = VM_details['cpu']
    vm_ram = VM_details['ram']
    vm_disk = VM_details['disk']

    #img_details_list
    # Schedular
    global selected_pm
    selected_pm = Scheduler(vm_cpu, vm_ram, vm_disk)
    #print selected_pm
    user_name = selected_pm.split("@")[0]
    #print list(user_name)
    global vm_image_path
    for vm in img_path_list:
        if vm[0] == VM_type_id:
            vm_image_name = vm[3].split("/")[-1].strip("\r")
            vm_image_path = vm[3].split(":")[0].strip("\r")
    send_image(selected_pm, vm_image_path)
    global VM
    
    if len(VM.keys())==0:
        i = 1
    else:
        i = int(VM.keys()[-1])+1
    vmid = i
    
    #imagePath = vm['name'].split(":")[0].strip("\r")
    xml="<domain type='qemu' id='"+str(i)+"'>    <name>"+str(VM_name)+"</name>    <memory unit='KiB'>"+str(int(vm_ram)*1024)+"</memory>    <vcpu placement='static'>"+str(vm_cpu)+"</vcpu>    <os>    <type arch='x86_64' machine='pc-i440fx-trusty'>hvm</type>    </os>    <devices>    <disk type='file' device='cdrom'>    <source file='"+str(vm_image_path)+"'/>    <target dev='hdc' bus='ide'/>    </disk>    </devices>    </domain>"""
    #img_path_list[]
#str(imagePath)
    try:
        conn = libvirt.open("qemu+ssh://"+str(selected_pm)+"/system")
        conn.defineXML(xml)
        dom = conn.lookupByName(VM_name)
        dom.create()
        result = "{\n%s\n}" % str(vmid)
        conn.close()
        VM[str(vmid)] = {}
        VM[str(vmid)]['Name'] = VM_name
        VM[str(vmid)]['PM'] = selected_pm
        VM[str(vmid)]['instance_type'] = VM_type_id
        VM[str(vmid)]['pmid'] = pmid[selected_pm]
        try :       
            fileopen = open("VM_INFO","a")
            toFile = str(vmid) +  "\t\t" + str(VM_name) + "\t\t" + str(selected_pm) + "\t\t" + str(VM_type_id) + "\t\t" + str(pmid[selected_pm]) + "\n"               
            fileopen.write(toFile)
            fileopen.close()
        except:
            print "unable to write to file"

        #return result
        return jsonify(vmid=str(vmid))
    except Exception,e: 
    	print str(e)
        #conn.close()
        #return str(0)
        res=str(vmid)
        return jsonify(success="0")


@app.route('/vm/query/' , methods = ['GET'])
def vm_query():

    args = request.args
    VM_id = str(args['vmid'])
    try:
        return jsonify(vmid=VM_id, name=VM[str(VM_id)]['Name'], instance_type=VM[str(VM_id)]['instance_type'], pmid=VM[str(VM_id)]['pmid'])
    except:
        return jsonify(success="0")

@app.route('/vm/destroy/' , methods = ['GET'])
def vm_destroy():
    try:
	args = request.args
	VM_id = str(args['vmid'])
	user= VM[str(VM_id)]['PM'].strip("@")[0]
	ip= VM[str(VM_id)]['PM'].strip("@")[1]
	print user	
	connect = libvirt.open("qemu+ssh://"+VM[str(VM_id)]['PM']+"/system")
	req = connect.lookupByName(VM[str(VM_id)]['Name'])
	if req.isActive():
	    req.destroy()
	req.undefine()
	
    	try:       
            fileopen = open("VM_INFO","r+")
            d = fileopen.readlines()
            fileopen.seek(0)
            for line in d:
                
                if line != str(VM_id) +  "\t\t" + str(VM[str(VM_id)]["Name"]) + "\t\t" + str(VM[str(VM_id)]["PM"]) + "\t\t" + str(VM[str(VM_id)]["instance_type"]) + "\t\t" + str(VM[str(VM_id)]["pmid"]) + "\n":
                    fileopen.write(line)
                    print line
                    print str(VM_id) +  "\t\t" + str(VM[str(VM_id)]["Name"]) + "\t\t" + str(VM[str(VM_id)]["PM"]) + "\t\t" + str(VM[str(VM_id)]["instance_type"]) + "\t\t" + str(VM[str(VM_id)]["pmid"]) + "\n"
            fileopen.truncate()
            fileopen.close()
        except:
            print "unable to write to file"
        del VM[str(VM_id)]
	return jsonify(status="1")
    except Exception,e: 
    	print str(e)
	return jsonify(status="0")

@app.route('/vm/types', methods=['GET'])
def vm_types():
    try:
        return jsonify(VMTypesDescription)
    except:
        return jsonify(status="0")

@app.route('/pm/list', methods=['GET'])
def list_pms():
    try:
        return jsonify(pmids=pmid.values())
    except:
        return jsonify(status="0")

@app.route('/pm/listvms', methods=['GET'])
def list_vms():
    args = request.args
    PM_id = str(args['pmid'])
    vm_list = [];
    try:
        for i in VM.iteritems():
            if(str(i[1]['pmid']) == PM_id):
                vm_list.append(i[0])
        return jsonify(vmids=vm_list)
    except:
        return jsonify(status="0")


@app.route('/pm/query', methods=['GET'])
def pm_query():
    args = request.args
    PM_id = str(args['pmid'])
    try:
        PM_ram = (subprocess.check_output(" ssh " + machines_list[int(PM_id) - 1] + "  free -m | grep 'Mem:' | awk '{ print $4 }'" , shell=True))
        PM_ram_total = (subprocess.check_output(" ssh " + machines_list[int(PM_id) - 1] + "  free -m | grep 'Mem:' | awk '{ print $2 }'" , shell=True))
        PM_cpu = int(subprocess.check_output(" ssh " + machines_list[int(PM_id) - 1] + " nproc" , shell=True))
        PM_ram = PM_ram.strip("\n")
        PM_ram_total = PM_ram_total.strip("\n")
        pm_disk_total = int(subprocess.check_output(" ssh " + machines_list[int(PM_id) - 1] + " df --total -TH --exclude-type=tmpfs | awk '{print $3}' | tail -n 1 | cut -b -3" , shell=True))
        pm_disk_free = int(subprocess.check_output(" ssh " + machines_list[int(PM_id) - 1] + " df --total -TH --exclude-type=tmpfs | awk '{print $5}' | tail -n 1 | cut -b -2" , shell=True))
        capacity = {'cpu':PM_cpu, 'ram':PM_ram_total, 'disk': str(pm_disk_total)}
        free = {'cpu': PM_cpu, 'ram': PM_ram, 'disk': str(pm_disk_free)}
        vm_count = 0;
        for pmm in VM.iteritems():
        	if(str(pmm[1]['pmid']) == PM_id):
        		vm_count = vm_count + 1
        return jsonify(pmid=PM_id, capacity=capacity, free=free, vms=vm_count)
    except Exception,e: 
        print str(e)
        return jsonify(status="0")

@app.route('/image/list', methods=['GET'])
def list_images():
    im = []
    try:
        for i in img_details_list:
    		im.append({'id':i[0], 'name':i[1]})
        return jsonify(images=im)
    except:
        return jsonify(status="0")


if __name__ == '__main__':
    global vm_types_filename
    vm_types_filename = sys.argv[3]
    jsonifyTypes(vm_types_filename)
    get_machines(sys.argv[1])
    get_images(sys.argv[2])
    try :       
        fileopen = open("VM_INFO","r+")
        d = fileopen.readlines()
        #fileopen.seek(0)
        if d == []:
            fileopen.write("VM_ID" +  "\t\t" + "VM_name" + "\t\t" + "selected_pm" + "\t\t" + "VM_type_id" + "\t\t" + "pmid" + "\n")
        else:
            for i in d:
                if(i == "VM_ID" +  "\t\t" + "VM_name" + "\t\t" + "selected_pm" + "\t\t" + "VM_type_id" + "\t\t" + "pmid" + "\n"):
                    continue
                j = i.split("\t\t")
                j[4] = j[0].strip("\n")
                VM[str(j[0])] = {}
                VM[str(j[0])]['Name'] = j[1]
                VM[str(j[0])]['PM'] = j[2]
                VM[str(j[0])]['instance_type'] = j[3]
                VM[str(j[0])]['pmid'] = j[4]
        fileopen.close()
    except Exception,e: 
        print str(e)
        print "unable to write to file"

    app.run(debug = True)
