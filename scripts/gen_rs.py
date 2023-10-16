#!/usr/bin/python3
import requests
import yaml
import sys
import subprocess
import os
import json
import time
from bird_parser import get_bird_session
client = yaml.safe_load( open("/root/arouteserver/clients_all.yml").read())
yaml.SafeDumper.ignore_aliases = lambda self, data: True

t1_asns = [ 701, 1239, 1299, 2914, 3257, 3320, 3356, 3491, 5511, 6453, 6461, 6762, 6830, 7018, 12956, 174, 1273, 2828, 4134, 4809, 4637, 6939, 7473, 7922, 9002 ]
stuix_members = [42,112,917,945,983,3856,6939,7480,13335,15169,16509,17415,18041,18178,18423,35384,38047,38254,38852,38856,44570,48024,50118,54625,57406,60326,61228,61302,63800,131149,131171,131642,131657,134823,135395,138211,138997,139247,140731,141237,142553,142641,147028,149423,149791,150173,151188,151338,199632,199688,201217,201801,202776,202820,202939,203283,203314,203423,204677,204844,205329,206003,207468,207469,207705,208137,209391,210445,210528,210932,211132,211323,211571,211946,212168,212331,212357,212358,212360,198304]

# get all as-set
client_list = client["clients"]
client_as_set = [(c["asn"],c["cfg"]["filtering"]["irrdb"]["as_sets"]) for c in client_list]
client_as_set = {c[0]:c[1] if c[1] != [] else ["AS" + str(c[0])] for c in client_as_set}
open("/root/gitrs/KSKB-IX/static/files/kskbix-all.yaml","w").write(yaml.safe_dump(client_as_set))

expire = 86400

irr_cache = {}
irr_cache_path = "/root/arouteserver/cache/irr_cache.json"
if os.path.isfile(irr_cache_path):
    try:
        irr_cache = json.loads(open(irr_cache_path).read())
    except:
        irr_cache = {}

def getinfo(as_set_all,af):
    if as_set_all in irr_cache and ( irr_cache[as_set_all]["time"] + expire ) > time.time():
        #print(as_set_all,irr_cache[as_set_all]["result"])
        return irr_cache[as_set_all]
    # irrdb = "RIPE,APNIC,AFRINIC,ARIN,LACNIC" # "RIPE,APNIC,AFRINIC,ARIN,NTTCOM,ALTDB,BBOI,BELL,JPIRR,LEVEL3,RADB,TC" 
    irrdb = "RIPE,APNIC,AFRINIC,ARIN,NTTCOM,ALTDB,BBOI,BELL,JPIRR,LEVEL3,RADB,TC"
    as_set = as_set_all
    if "::" in as_set_all:
        irrdb,as_set = as_set.split("::")
    #print(" ".join(["bgpq4", "-" + str(af), "-b", "-R", "48","-S",irrdb, "-m", "48" , as_set]))
    bgpq4_out = subprocess.run(["bgpq4", "-" + str(af), "-b", "-R", "48","-S",irrdb, "-m", "48" , as_set], stdout=subprocess.PIPE)
    bgpq4_asns = subprocess.run(["bgpq4", "-" + str(af), "-tj", "-S",irrdb , as_set], stdout=subprocess.PIPE).stdout.decode()
    asset_asns = json.loads(bgpq4_asns)["NN"]
    irr_cache[as_set_all] = {}
    irr_cache[as_set_all]["ASNs"] = asset_asns
    irr_cache[as_set_all]["prefix_num"] = max(0,len(bgpq4_out.stdout.decode().split("\n"))-2)
    irr_cache[as_set_all]["time"] = time.time()
    irr_cache[as_set_all]["t1_asns"] = sorted(set(asset_asns) & set(t1_asns))
    #print(as_set_all,irr_cache[as_set_all]["result"])
    return irr_cache[as_set_all]


if sys.argv[1] == "2":
    for ci in range(len(client["clients"])):
        the_asn = client["clients"][ci]["asn"]
        del  client["clients"][ci]["name"]
        as_sets_new = []
        for as_set in client["clients"][ci]["cfg"]["filtering"]["irrdb"]["as_sets"]:
            as_set_info = getinfo(as_set,6)
            if int(the_asn) in stuix_members:
                if "attach_custom_communities" not in client["clients"][ci]["cfg"]:
                    client["clients"][ci]["cfg"]["attach_custom_communities"] = ["as_path_from_stuix"]
                else:
                    client["clients"][ci]["cfg"]["attach_custom_communities"] +=  ["as_path_from_stuix"]
            elif "enforce_origin_in_as_set" in client["clients"][ci]["cfg"]["filtering"]:
                if "attach_custom_communities" not in client["clients"][ci]["cfg"]:
                    client["clients"][ci]["cfg"]["attach_custom_communities"] = ["as_path_from_stuix"]
                else:
                    client["clients"][ci]["cfg"]["attach_custom_communities"] +=  ["as_path_from_stuix"]
            elif as_set_info["prefix_num"] <= 100 and as_set_info["t1_asns"] == []:
                as_sets_new += [as_set]
            else:
                if as_set_info["t1_asns"] != []:
                    print("Warning:",as_set ,"contains t1_asns:",as_set_info["t1_asns"])
        client["clients"][ci]["cfg"]["filtering"]["irrdb"]["as_sets"] = as_sets_new
    client_rs2_txt = yaml.safe_dump(client, sort_keys=False)
    open("/root/arouteserver/clients_rs2.yml","w").write(client_rs2_txt)
if sys.argv[1] == "1":
    for ci in range(len(client["clients"])):
        the_asn = client["clients"][ci]["asn"]
        del  client["clients"][ci]["name"]
        as_sets_new = []
        for as_set in client["clients"][ci]["cfg"]["filtering"]["irrdb"]["as_sets"]:
            as_set_info = getinfo(as_set,6)
            if as_set_info["t1_asns"] == []:
                as_sets_new += [as_set]
            else:
                if as_set_info["t1_asns"] != []:
                    print("Warning:",as_set ,"contains t1_asns:",as_set_info["t1_asns"])
        client["clients"][ci]["cfg"]["filtering"]["irrdb"]["as_sets"] = as_sets_new
        client["clients"][ci]["cfg"]["filtering"]["irrdb"].pop("enforce_origin_in_as_set",None)
        client["clients"][ci]["cfg"]["filtering"]["irrdb"].pop("enforce_prefix_in_as_set",None)
        client["clients"][ci]["cfg"]["filtering"].pop("transit_free",None)
        client["clients"][ci]["cfg"]["filtering"].pop("max_prefix",None)
        my_as_sets = client["clients"][ci]["cfg"]["filtering"]["irrdb"]["as_sets"]
    client_rs1_txt = yaml.safe_dump(client, sort_keys=False)
    open("/root/arouteserver/clients_rs1.yml","w").write(client_rs1_txt)
open(irr_cache_path,"w").write(json.dumps(irr_cache,indent=4))
