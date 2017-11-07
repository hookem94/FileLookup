#!/usr/bin/env python

# FileLookup.py was created by Glenn P. Edwards Jr.
#	http://hiddenillusion.blogspot.com
#		@hiddenillusion
# Forked by @hookem94
# Date: 11-07-2017
# version = 0.3.2

# Requirements:
#	- Internet Access :)
#	- VirusTotal API key if you want prettier reports with more information from the JSON object
# Optional:
#	- SimpleJson module to print the pretty reports (optional but is nicer)
# To-Do:
#	- Bit9 File Advisor
#	- OpenMalware (http://oc.gtisc.gatech.edu:8080/search.cgi?search=)
#	- Threading
#	- Pretty up the code
#	- This really would be easier if I used BS4 in the beginning :/

import os
import sys
from datetime import datetime
import argparse
import binascii
import re
import hashlib
import socket
import urllib
import urllib2
from time import localtime, strftime
try :
    import simplejson
    sjson = True
except ImportError:
    sjson = False
    pass

# Configure some user-specific info
vt_key = ""
if not re.match('\w+', vt_key):
    print "[!] You must configure your VirusTotal API key"
    sys.exit()

def main():
    # Get program args
    parser = argparse.ArgumentParser(description='Searches various online resources to try and get as much info about a file as possible without submitting it, requiring third party modules or performing any analysis on the file.')
    parser.add_argument('-f', '--file', help='Path to directory/file(s) to be scanned')
    parser.add_argument('-H', '--hash', help='MD5 hash to be queried')
    
    args = vars(parser.parse_args())

    md5 = ''
			
    def doWork(obj):
        if args['hash']: 
            md5 = args['hash']	
        else:
            md5 = md5sum(file)
        results = []
        results.append(("#" * 80) + "\nFile:\t %s\n" % obj + ("#" * 80))
        results.append("MD5:\t\t\t%s" % md5)
        if args['file']:		
            results.append("Sha256:\t\t\t%s" % sha256sum(file))	
        results.append("VirusTotal:\t\t%s" % virustotal(md5))		
        results.append("Cymru:\t\t\t%s" % cymru(md5))
        results.append("ShadowServer A/V:\t%s" % ss_av(md5))
        results.append("ShadowServer Known:\t%s" % ss_known(md5))	
        results.append("ThreatExpert Known:\t%s" % threatexpert(md5)) 		
        results.append("")
		
        print '\n'.join(results)	
		
    # Verify we have something to do
    if not args['file'] and not args['hash']:
        print "[!] I need something to do"
        sys.exit()
		
    # Verify supplied path exists or die
    if args['file']:
        if not os.path.exists(args['file']):
            print "[!] The supplied path does not exist"
            sys.exit()
        else:
	        # Set the path to file(s)
            file = args['file']	
            if os.path.isdir(file):
                # Recursivly walk the supplied path and process files accordingly
                for root, dirs, files in os.walk(file):
                    for name in files: 
                        f = os.path.join(root, name)	
                        doWork(f)				
            elif os.path.isfile(file):
                doWork(file)			

    # Verify the hash is legit
    if args['hash']:
        if not re.findall(r"([a-fA-F\d]{32})", args['hash']):
            print "[!] The supplied path does not exist"
            sys.exit()	
        else:	
            doWork(args['hash'])
	
def md5sum(file):
    try:
        f = open(file, "rb")
        data = f.read()
        md5 =  hashlib.md5(data).hexdigest()
        f.close()
    except Exception, msg:
        print msg

    return md5

def sha256sum(file):
    try:
        f = open(file, "rb")
        data = f.read()
        sha256 =  hashlib.sha256(data).hexdigest()
        f.close()
    except Exception, msg:
        print msg

    return sha256

def virustotal(hash):
    """
    Return percent of A/V hits from VirusTotal scan report of the file if one exists.
    """
    url = "https://www.virustotal.com/vtapi/v2/file/report"
    parameters = {"resource": hash, "apikey": vt_key}
    data = urllib.urlencode(parameters)
    req = urllib2.Request(url, data)
    response = urllib2.urlopen(req)
    result = response.read()
    out = []
    out.append('')

    try:
        if not sjson == False:
            rpt = simplejson.loads(result)
            date = rpt["scan_date"].split(' ')[0]
            new_date = datetime.strptime(date, "%Y-%m-%d").strftime("%b %d %Y")
            out.append("\tScan Date:\t %s" % new_date)
            out.append("\tTotal Engines:\t %s" % rpt["total"])
            out.append("\tDetected:\t %s" % rpt["positives"])
            out.append('')
            out.append("\tA/V Results:")
            out.append("\t\t\tClamAV:\t\t %s" % rpt["scans"]["Microsoft"]["result"])
            out.append("\t\t\tKaspersky:\t %s" % rpt["scans"]["Kaspersky"]["result"])
            out.append("\t\t\tMcAfee:\t\t %s" % rpt["scans"]["McAfee"]["result"])
            out.append("\t\t\tMicrosoft:\t %s" % rpt["scans"]["Microsoft"]["result"])
            out.append("\t\t\tSophos:\t\t %s" % rpt["scans"]["Sophos"]["result"])
            out.append("\t\t\tSymantec:\t %s" % rpt["scans"]["Symantec"]["result"])
            out.append("\tLink: %s" % rpt["permalink"])
        else:
            # Still return  VT results, just not as pretty without SimpleJson	
            col = result.split(',')
            for line in col:
                l = line.replace('\"', '')
                if "scan_date:" in l:
                    date = l.replace('\"', '').replace(' scan_date: ', '').split(' ')[0]		
                    new_date = datetime.strptime(date, "%Y-%m-%d").strftime("%b %d %Y")				
                    out.append("\tScan Date:\t%s" % new_date)
                elif "positives:" in l:
                    out.append("\tDetected:\t%s" % l.replace('\"', '').replace(' positives: ', ''))
                elif "total:" in l:
                    out.append("\tTotal Engines:\t%s" % l.replace('\"', '').replace(' total: ', ''))		

        result = '\n'.join(out)
        if result == None:
            result = "No Match"	
        return result
    except Exception:
        result = "No Match"	
        return result
		
def ss_known(hash):
    """
    Based off original by:  Jose Nazario (jose@arbor.net)
    site : http://bin-test.shadowserver.org
    """
    url = "http://bin-test.shadowserver.org/api"
    data = {}
    data['md5'] = hash
    url_vals = urllib.urlencode(data)
    req = urllib2.Request(url, data)
    full_url = url + '?' + url_vals
    response = urllib2.urlopen(full_url)
    result = response.read()
    
    count = 0
    for line in result.split('\n'):
        count += 1
        if count < 2 :
            result = "No Match"
        else:
            l = line.split(' ', 1)
            if len(l) == 2:
                try: res[l[0]] = simplejson.loads(l[1])
                except: pass
			
    return result
	
def ss_av(hash):
    """
    Based off original by:  Jose Nazario (jose@arbor.net)
    site : http://innocuous.shadowserver.org/api/?query=#md5-or-sha1#	
    """
    url = "http://innocuous.shadowserver.org/api/"
    data = {}
    data['query'] = hash
    url_vals = urllib.urlencode(data)
    req = urllib2.Request(url, data)
    full_url = url + '?' + url_vals
    response = urllib2.urlopen(full_url)
    result = response.read()

    if "No match" in result:
        result = "No Match"
    elif "Whitlisted" in result:
        result = "Whitelisted"
    else:
        lines = result.split('\n')
        out = []
        col = lines[0].split(',')
        av = lines[1].split(',')
        out.append('')
        fdate = col[2].replace('\"', '').split(' ')[0]	
        fnew_date = datetime.strptime(fdate, "%Y-%m-%d").strftime("%b %d %Y")
        out.append("\tFirst Seen:\t%s" % fnew_date)
        ldate = col[2].replace('\"', '').split(' ')[0]
        lnew_date = datetime.strptime(ldate, "%Y-%m-%d").strftime("%b %d %Y")
        out.append("\tLast Seen:\t%s" % lnew_date)
        out.append('')
        out.append("\tA/V Results:")
        if len(av) > 1:
            for i in av:
                out.append("\t\t\t%s" % i.replace('\"','').replace('{', '').replace('}', ''))
        else:
            out.append("\t\t\tN/A")

        result = '\n'.join(out)

    return result

def cymru(hash):
    """
    Return Team Cymru Malware Hash Database results.
    source: http://code.google.com/p/malwarecookbook/
    site : http://www.team-cymru.org/Services/MHR/
    """
    request = '%s\r\n' % hash
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect(('hash.cymru.com', 43))
        s.send('begin\r\n')
        s.recv(1024)
        s.send(request)
        response = s.recv(1024)
        s.send('end\r\n')
        s.close()
        if len(response) > 0:
            resp_re = re.compile('\S+ (\d+) (\S+)')
            match = resp_re.match(response)
            result = "\n\tLast Seen:\t%s\n\tDetected:\t%s" % (strftime("%b %d %Y", localtime(int(match.group(1)))), match.group(2))
    except socket.error:
        result = "Error"
		
    return result		
	
def threatexpert(hash):
    """
    Return existence of report in ThreatExpert database.
    site   : http://www.threatexpert.com
	credit : Added 11/29/2012 by Keith Gilbert - @digital4rensics  
	note   : Greatly increases time required  
    """
    result = []		
    url = 'http://threatexpert.com/report.aspx?md5=' + hash
    try:
        page = urllib2.urlopen(url).read()
        for line in page.split('\n'):
            if line.find('Submission Summary:'):
               result.append("Report Found")
               result.append("\tLink: %s" % url)	
               return '\n'.join(result)
            else:
                return "No Match"
    except Exception:
        return "Error"	

if __name__ == "__main__":
	main()  
