#!/usr/bin/python3
"""
    Author: Bryce Verdier
    Date: 2/8/2011

    Description: Read a new line delimited file of 
        unix based hosts and gather the /etc/passwd data from
        each host. Parsing accounts from each host, and keeping
        track of which host has which account UID number. Uses files 
        to help with the process of making the whole script multi-
        process.
"""

import subprocess
import sys
import os
import csv
import itertools
from optparse import OptionParser
from multiprocessing import Pool

class Account(object):
    def __init__(self, name, uid, gid, servername):
        self._name = name
        self._uid = {uid : [servername]}
        self._gid = {gid : [servername]}
         
    @property
    def get_name(self):
        return str(self._name)

    @property
    def uid_length(self):
        return str(len(self._uid))

    @property
    def gid_length(self):
        return str(len(self._gid))

    def update_uid(self, uid, servername):
        if uid in self._uid.keys():
            self._uid[uid].append(servername)
        else:
            self._uid[uid] = [servername]

    def update_gid(self, gid, servername):
        if gid in self._gid.keys():
            self._gid[gid].append(servername)
        else:
            self._gid[gid] = [servername]

    @property
    def uid_output(self):
        if len(self._uid) > 1:
            print(self.get_name + ":")
            for k,v in self._uid.items():
                print("\t" + k + ":  " + self.uid_length)
                for items in v:
                    print("\t\t" + items + ", ")

class Accounts(list):
    def __init__(self):
        self._list = []
        self._index = 0 

    def __contains__(self, name):
        """ used for 'in' keyword. Needed to make the 'in accounts'
            line function properly.
        """
        for hosts in self._list:
            if name == hosts.get_name:
                return True

        return False

    def __iter__(self):
        return self

    def __next__(self):
        if self._index >= len(self._list):
               raise StopIteration
        self._index += 1
        return self._list[self._index - 1]

    def extended_append(self, accountname, uid, gid, server):
        for hosts in self._list:
            if accountname == hosts.get_name:
                hosts.update_uid(uid, server)
                hosts.update_gid(gid, server)
                return
        
        # if we've made it this far, the account object is not in 
        # the list
        self._list.append(Account(accountname, uid, gid, server))

def get_all_ssh_files(directory):
    try:
        return [ x for x in os.listdir(directory + '/ssh') ]

    except OSError:
        return []

def get_all_error_files(directory):
    try:
        return [ x for x in os.listdir(directory) if x != 'ssh']

    except OSError:
        return []

def get_external_passwd(dir_host_tupl):
    directory = dir_host_tupl[0]
    hostname = dir_host_tupl[1]

    command = "ssh " + hostname + " less /etc/passwd | cut -d ':' -f 1,3,4"
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    (proc, error) = process.communicate()
    sys.stdout.flush()

    if error:
        f = open(directory + '/' + hostname.strip('"'), 'w')
        f.write(error.decode())
        f.close
        return

    # using the 'if lines' to remove any empty lines
    f = open(directory + '/ssh/' + hostname.strip('"'), 'w')
    [ f.write(lines) for lines in proc.decode() if lines ]
    f.close()

def mk_tmp_python_dir(directory):
    try:
        os.mkdir(directory)
        os.mkdir(directory + '/ssh/')
    except OSError:
        pass

def read_hosts_file(filename):
    with open(filename, 'r') as f:
        file_data = [ lines.strip('\n') for lines in f ] 

    return file_data

def read_ssh_file(filename):
    try:
        f = csv.reader(open(filename, 'r', newline=''), delimiter=':')
        return (filename, [ lines for lines in f ] )
    except OSError:
        return (0, 0)

def rm_tmp_python_dir(directory):
    try:
        [ os.remove(directory + '/ssh/' + x) for x in os.listdir(directory + '/ssh') ]
        os.rmdir(directory + '/ssh')
        [ os.remove(directory + '/' + x) for x in os.listdir(directory) ]
        os.rmdir(directory)

    except OSError:
        pass

if __name__ == "__main__":
    usage = "%prog [options]"
    parser = OptionParser(usage=usage)
    parser.add_option("-f", "--file", dest="filename", 
        help="""Path to newline delimited file, of which computer's 
                /etc/passwd to parse and count.""")
    parser.add_option("-d", "--dir", dest="directory", default='/tmp/python',
        help='''Path to put the temporary ssh files.
                NOTE: defaults to /tmp/python''')
    
    (options, args) = parser.parse_args()
    
    if not options.filename:
        print("The file (-f) argument "\
              "is nessacary to run this program.\n")
        parser.print_help()
        sys.exit(1)

    #things start to happen here
    mk_tmp_python_dir(options.directory)

    accounts = Accounts()
    hosts = read_hosts_file(options.filename)

    #Start the Pools
    p = Pool(processes=5)

    # because p.map can only take 1 argument, zip up the two items needed
    # for the get_external_passwd function
    zipped_argument = zip(itertools.repeat(options.directory), hosts)
  
    p.map(get_external_passwd, zipped_argument)
   
    #read in all files and put into proper memory recepticles.
    for hosts in get_all_ssh_files(options.directory):
        host_data = read_ssh_file(options.directory + '/ssh/' + hosts)
        if isinstance(host_data, tuple):
            # dynamically splicing to remove the path before the filename"
            host_name = str(host_data[0])[len(options.directory) + 5:]
            for a in host_data[1]:
                # in case of rogue blank lines in the host_data 
                try:
                    accounts.extended_append(a[0], a[1], a[2], host_name)
                except IndexError:
                    continue

        else:
            print('Error with file: ' + host_data[0])
            continue

    [ acct.uid_output for acct in accounts ]
    
    print("\nHosts that were not completed:",  file=sys.stderr)
    print(*get_all_error_files(options.directory), sep='\n', file=sys.stderr)

    rm_tmp_python_dir(options.directory)
