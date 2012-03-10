#!/usr/bin/python
import os
import time



def get_sector_size(dev):
    f=file("/sys/block/"+dev+"/queue/physical_block_size", 'r')
    return int(f.readline())

def get_stat(dev):
    '''
    return new stat values (absolute numbers) for specified device
    return values as dictionary or None if error occure

    format from linux Documentation/block/stat.txt:

    Name            units         description
    ----            -----         -----------
    read I/Os       requests      number of read I/Os processed
    read merges     requests      number of read I/Os merged with in-queue I/O
    read sectors    sectors       number of sectors read
    read ticks      milliseconds  total wait time for read requests
    write I/Os      requests      number of write I/Os processed
    write merges    requests      number of write I/Os merged with in-queue I/O
    write sectors   sectors       number of sectors written
    write ticks     milliseconds  total wait time for write requests
    in_flight       requests      number of I/Os currently in flight
    io_ticks        milliseconds  total time this block device has been active
    time_in_queue   milliseconds  total wait time for all requests

    return value is just dictionary of those values (11 items)
    '''
    retval={}
    f=open('/sys/block/'+dev+'/stat','r')
    split=f.readline().split()
    retval["read_ios"]      = int(split[0])
    retval["read_merges"]   = int(split[1])
    retval["read_sectors"]  = int(split[2])  #TODO add getdevsize for right IO in MB/s calculation
    retval["read_ticks"]    = int(split[3])
    retval["write_ios"]     = int(split[4])
    retval["write_merges"]  = int(split[5])
    retval["write_sectors"] = int(split[6])
    retval["write_ticks"]   = int(split[7])
    retval["in_flight"]     = int(split[8])
    retval["io_ticks"]      = int(split[9])
    retval["time_in_queue"] = int(split[10])

    return retval


def is_any_io(item):
    '''
        return True if print device data, return false if not
        will be full featured, right now it or filter empty, or show all
    '''
    return bool ( filter( lambda x: x>0, item.values() ) )


def devlist(config):
    '''
    scan devices in /sys/block according to config file
    if config is none, every device is scanned

    return dictionary of found devices or empty dict
    we add only keys 'sector size' and 'id'
    '''
    devs={}
    for dev in  os.listdir('/sys/block'):
        #skip empty devices never has an IO
	if is_any_io(get_stat(dev)):
            devs[dev]={}
            devs[dev]['sector_size']=get_sector_size(dev) #(just for test) FIXME
            devs[dev]['id']='FIXME' #FIXME
    return devs



def calc_single_delta(new,old, sector_size):
    '''
    return 'delta' values between old and new
    format is same as get_stat, but contains delta, not absolute values
    (N.B. delta is absolute and does not divided for dt)
    in certain cases we return not delta, but actual value (f.e. in_flight)
    '''
    retval={}
    #real deltas
    for key in ('read_ios', 'read_merges', 'read_sectors', 'read_ticks', 'write_ios', 'write_merges', 'write_sectors', 'write_sectors', 'write_ticks', 'io_ticks', 'time_in_queue'):
        retval[key]=new[key]-old[key]
    #copy as is
    retval['in_flight']=new['in_flight']
    retval['read_sectors']*=sector_size
    retval['write_sectors']*=sector_size
    try:
        retval['latency']=float(retval['time_in_queue'])/(retval['read_ios']+retval['write_ios'])  #avg=(new_time-old_time)/IOPS
    except ZeroDivisionError:
        retval['latency']=0 #By authority decision zero devided to zero is equal to zero. dixi. 
    return retval

def calc_delta(old, new, devlist):
    '''
       return dict of deltas for two dict of dicts
    '''
    retval={}
    for key in old.iterkeys():
        retval[key]=calc_single_delta(new[key],old[key],devlist[key]["sector_size"])
	
    return retval

def scan_all(devlist):
    '''
        performs full scan for all devices in devlist
        return dict in format:
          key=devname
          values=dict of stat
    '''
    retval={}
    for dev in devlist.keys():
        retval[dev]=get_stat(dev)
    return retval

def tick(devlist, delay):
    '''
        yield new delta for all devices in devlist
    '''
    old=scan_all(devlist)
    while 1:
        time.sleep(delay)
        new=scan_all(devlist)
        yield calc_delta (old,new,devlist)
	old=new

def get_top (delta):
    '''
       scan through all deltas and sort them
    '''
    return delta #FIX


def make_k (n):
    '''
        return human-like view
    '''
    if n < 10000:
        return str(n)
    if  n < 100000000:
        return str(n/1000)+'k'
    return str(n/1000000)+'M'

def fix (l):
    '''
       create pagination and convert numeric values to ISO-based format (f.e. 1k 8M and so on)
    '''
    if type(l) == type(""):
	value=l[0:8]
    elif type(l) == type(0.0):
        value = make_k ( round(l,2)) 
    else:
	value = make_k(l)
    return  value.rjust(8, ' ')

def prepare_header():
    '''
       create header line (reset screen and inversion).
       see man console_codes for detail
    '''
    fields=('Dev name', 'r IOPS', 'w IOPS',  'w bytes', 'r bytes', 'latency', 'queue')
    f=" ".join([fix(a) for a in fields])
    return '\x1bc\x1b[7m'+f+'\x1b[0m'

def prepare_line(name,item):
    '''
       return string for printing for 'item'
    '''
    fields=('read_ios', 'write_ios', 'read_sectors', 'write_sectors', 'latency', 'in_flight')
    f=" ".join(map(fix,[name]+[ item[i] for i in fields]))
    return f


def view(delta):
    '''
        Visualisation part: print (un)fancy list
    '''
    print prepare_header()
	
    for a in get_top(delta).iterkeys():
        print prepare_line(a,delta[a])
    return None

def main():
    '''
    Right now we don't accept any command line values and 
    don't use config file (initial proof of usability)
    We making 1s tick so we can use delta as ds/dt
    '''
    config=None
    for a in tick(devlist(config),1):
	view (a)

if __name__ == '__main__':
    main ()

