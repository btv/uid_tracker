#!/usr/bin/python3
"""
    Author: Bryce Verdier
    Date: 2/8/2011

    Description: Read a new line delimited file of 
        unix based hosts and gather the /etc/passwd data from
        each host. Parsing accounts from each host, and keeping
        track of which host has which account UID number.
"""

import subprocess
import sys
from optparse import OptionParser

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

    def append(self, account):
        self._list.append(account)

    def extended_append(self, accountname, uid, gid, server):
        for hosts in self._list:
            if accountname == hosts.get_name:
                hosts.update_uid(uid, server)
                hosts.update_gid(gid, server)

def read_file(filename):
    with open(filename, 'r') as f:
        file_data = [lines.strip('\n') for lines in f] 

    return file_data

def get_external_passwd(hostname):
    command = "ssh " + hostname + " less /etc/passwd | cut -d ':' -f 1,3,4"
    process = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
    (proc, error) = process.communicate()
    sys.stdout.flush()

    if error:
        print(error)
        return []

    # using the 'if lines' to remove any empty lines
    return [lines for lines in proc.decode().split('\n') if lines]

if __name__ == "__main__":
    usage = "%prog [options]"
    parser = OptionParser(usage=usage)
    parser.add_option("-f", "--file", dest="filename", 
        help="""Path to newline delimited file, of which computer's 
                /etc/passwd to parse and count.""")
    
    (options, args) = parser.parse_args()
    
    if not options.filename:
        print("The file (-f) argument "\
              "is nessacary to run this program.\n")
        parser.print_help()
        sys.exit(1)

    accounts = Accounts()
    hosts = read_file(options.filename)
    for host in hosts:
        host_data = get_external_passwd(host)
        if not host_data:
            continue
        for ids in host_data:
            data = ids.split(':')
            if data[0] in accounts:
                accounts.extended_append(data[0], data[1], data[2], host)
            else:
                accounts.append(Account(data[0], data[1], data[2], host))

    for account in accounts:
        account.uid_output
