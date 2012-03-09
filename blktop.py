#!/usr/bin/python
import os
import time

def devlist(config):
    '''
    scan devices in /sys/block according to config file
    if config is none, every device is scanned

    return dictionary of found devices or empty dict
    we add only keys 'sector size' and 'id'
    '''
    devs={}
    for dev in  map(lambda x: '/sys/block/' + x, os.listdir('/sys/block')):
        devs[dev]={}
        devs[dev]['sector_size']=512 #(just for test) FIXME
        devs[dev]['id']='FIXME' #FIXME
    return devs

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
    f=open(dev+'/stat','r')
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

def calc_single_delta(new,old):
    '''
    return 'delta' values between old and new
    format is same as get_stat, but contains delta, not absolute values
    (N.B. delta is absolute and does not divided for dt)
    in certain cases we return not delta, but actual value (f.e. in_flight)
    '''
    retval={}
    #real deltas
    for key in ('read_ios', 'read_merges', 'read_sectors', 'read_ticks', 'write_ios', 'write_merges', 'write_sectors', 'write_sectors', 'write_ticks', 'io_ticks'):
        retval[key]=new[key]-old[key]
    #copy as is
    retval['in_flight']=new['in_flight']
    try:
        retval['time_in_queue']=float (new['time_in_queue']-old['time_in_queue'])/(retval['read_ios']+retval['write_ios'])  #avg=(new_time-old_time)/IOPS
    except ZeroDivisionError:
        retval['time_in_queue']=0 #By authority decision zero devided to zero is equal to zero. dixi. 
    return retval

def calc_delta(old, new):
    '''
       return dict of deltas for two dict of dicts
    '''
    retval={}
    for key in old.iterkeys():
        retval[key]=calc_single_delta(new[key],old[key])
#        if key == '/sys/block/sda':
#		print "debug", "-"*40+'\n',new[key],'\n'+'-'*40+'\n', old[key], '\n'+'='*50+'\n'
#		print retval[key]
	
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
        yield new values
    '''
    old=scan_all(devlist)
    while 1:
        time.sleep(delay)
        new=scan_all(devlist)
        yield calc_delta (old,new)
	old=new

def get_top (delta):
    '''
       scan through all deltas and sort them
    '''
    return delta #FIX

def clear_name(name):
    '''strip off /dev/ part from device name'''
    return name[name.rfind('/'):]

def prepare_line(name,item):
    '''
       return string for printing for 'item'
    '''
    fix=lambda l: repr(l)[0:12].rjust(12, ' ')
    return fix(clear_name(name))+" ".join(map(fix,item.values()))


def is_show(dev,item):
    '''
        return True if print device data, return false if not
        will be full featured, right now it or filter empty, or show all
    '''
#    return bool ( filter( lambda x: x>0, item.values() ) )
    return True

def view(delta):
    '''
        Visualisation part: print (un)fancy list
    '''
    print "\x1bc"
    fix=lambda l: str(l)[0:12].rjust(12, ' ')
    print " ".join ([fix(a) for a in ["dev name"]+delta.values()[0].keys()])
        
	
    for a in get_top(delta).iterkeys():
#        print a, delta[a]['write_sectors']
        if is_show (a, delta[a] ):
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

