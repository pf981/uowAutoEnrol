#!/usr/bin/python
# #!/bin/python # Use this for Solaris (Banshee)
"""
This script will continuously attempt to enrol a student in a given tutorial name (e.g. "AUTM-INFO411/911-CL/01")
Requires username, password and the computer lab enrolment link obtained from the text on the right side of the table located at "tutorial enrolment"->"continue.g.
https://solss.uow.edu.au/sid/tutorial_enrolment.display_tutorial_timetable?p_sub_inst_id_pri=202385&p_sub_inst_id_ori=202385&p_type_id=10&p_student_number=1234567&p_session_id=NLJWCPGGFPHUAWNSQXBYHFPCMJTSZWIN&p_screen=tut_enrol&p_cs=4092098302739765654

POST data to sols.

POST data was manually observed using Firefox with the Tamper Data extension and looking at source.

Note that is seems that when a session modifies information on Sols' database, it will invalidate
all other sessions.

Testing cannot really be done until enrolment opens...

It appears that if you logon to Sols too much it suspects something is wrong and will require your next logon to provide a student number, barcode and date of birth. When used properly, this program should not frequently start new sessions so this shouldn't be a problem. This program does not have any means of determining if this has occured and will not fix itself if this happens.
"""

__version__ = "0.1.0"
__author__ = "Paul Foster"
__date__ = "12-02-2012"

import sys, urllib2, urllib, re
from optparse import OptionParser

from padnums import pprint_table

parser = OptionParser()
parser.add_option("-u", "--username", dest="username",
                  help="UOW SOLs username login (mandatory)", metavar="USERNAME")
parser.add_option("-p", "--password", dest="password",
                  help="UOW SOLs password login (mandatory)", metavar="PASSWORD")
parser.add_option("-i", "--p_sub_inst_id_ori", dest="p_sub_inst_id_ori",
                  help="The value of this is found in the link on the right column of the table at \"tutorial enrolment\"->\"continue\"", metavar="INSTID")
parser.add_option("-s", "--tut_string", dest="tut_string",
                  help="Text on the left side of the table located at \"tutorial enrolment\"->\"continue\"->[lab/tutorial]. Eg \"AUTM-INFO411/911-CL/01\" (mandatory)", metavar="TUTSTRING")
(opts, args) = parser.parse_args()

mandatories = ['username', 'password', "p_sub_inst_id_ori", "tut_string"]
for m in mandatories:
    if not opts.__dict__[m]:
        print "mandatory option is missing\n"
        parser.print_help()
        exit(-1)
username = opts.username
password = opts.password
p_sub_inst_id_ori = opts.p_sub_inst_id_ori
tut_string = opts.tut_string

def postAndGetReply(url, postData):
    """This function posts the postData to the url.
    Args:
        url (str): The url to post to
        postData ((str, str)[]): The array of variable names and values

    Returns:
        The file descriptor of the reply
    """
    req = urllib2.Request(url)
    req.add_header("Content-type", "application/x-www-form-urlencoded")
    return urllib2.urlopen(req, postData)

def startNewSession():
    """This function gets a session id and student number by sending a post request to sols
    Returns:
        (str). The session id.
    """
    url = 'https://solss.uow.edu.au/sid/sols_logon.validate_sols_logon'
    postData = urllib.urlencode([('p_username', username),('p_password', password)])
    fd = postAndGetReply(url, postData)

    # Find the session id in the reply
    while 1:
        data = fd.readline()
        if not len(data):
            sys.stderr.write("Error: could not find session id in login reply data - probably invalid login credentials.")
            sys.exit(1)
        matchedStudentNum = re.search('p_student_number=([0-9]*)', data)
        matchedSessionId = re.search('p_session_id=([A-Z]*)', data)
        if matchedStudentNum:
            studentNum = matchedStudentNum.group(1)
        if matchedSessionId:
            return (matchedSessionId.group(1), studentNum)

# returns the p_cs variable
# This variable is different to the one we get from logging in. It is probably some kind of session id.
def getCs1(sessionId, studentNum):
    """This function gets the first p_cs variable. It is different to the one we get from logging in. It is probably some kind of session id.
    It comes from the menu
    Args:
        sessionId (str): The session ID to post
        studentNum str: The student number to post

    Returns:
        str. The p_cs variable (cs1)
    """
    url = 'https://solss.uow.edu.au/sid/sols_menu.display_sols_menu'
    postData = urllib.urlencode([('p_system', 'STUDENT'),('p_menu_name', 'MAIN_MENU'),('p_student_number',studentNum),('p_session_id',sessionId)])
    fd = postAndGetReply(url, postData)

    # Find the session id in the reply
    while 1:
        data = fd.read(1024)
        if not len(data):
            sys.stderr.write("Error: could not find p_cs in main menu reply data.")
            sys.exit(1)
        matchedCs1 = re.search('p_cs=([0-9]*)', data)
        if matchedCs1:
            return matchedCs1.group(1)

class SessionExpiredError(Exception):
    pass

def getProcessEnrolmentLink(timetableUrl, tut_string):
    """Find the enrolment link in the timetable. If the link is not there (ie It is before the enrolment is open) it will return None.
       Once it has found the link it will change it from "tutorial_enrolment.confirm_enrol" to "tutorial_enrolment.process_enrol". (So when you open it it will fully enrol you not just take you to a confirmation page)

    Returns:
        processEnrolmentLine (str). The modified url and postData for this link and session
    """

    fd = urllib2.urlopen(timetableUrl)

    for line in fd:
        # if it doesn't have some text indicating that the session is valid
                 #raise SessionExpiredError()

        match = re.search("href=\"(.*?)\">.*%s" % tut_string, line)# if the table has a link (ie enrolments have opened)
        if match:
            return "https://solss.uow.edu.au/sid/%s" % re.sub(r'tutorial_enrolment.confirm_enrol', r'tutorial_enrolment.process_enrol', match.group(1))


def getTimetableLink(studentNum, sessionId, cs1):
    """Gets the link to the enrolment timetable
    Args:
        studentNum (str): Student number
        sessionId (str): The session ID of the current session
        cs1 (str): The p_cs variable obtained from getCs1

    Returns:
        url (str): The url with full post data for the timetable
    """
    fd = urllib2.urlopen('https://solss.uow.edu.au/sid/tutorial_enrolment.display_tutorial?p_student_number=%s&p_session_id=%s&p_cs=%s&p_submit=Continue' % (studentNum, sessionId, cs1))

    for line in fd:
        match = re.search("href=\"(.*?p_sub_inst_id_ori=%s.*?)\">" % p_sub_inst_id_ori, line)
        if match:
            return "https://solss.uow.edu.au/sid/%s" % match.group(1)

def __main__():
    processEnrolmentLink = None
    while not processEnrolmentLink:
        (sessionId, studentNum) = startNewSession()
        timetableUrl = getTimetableLink(studentNum, sessionId, getCs1(sessionId, studentNum))

        # Print session information in a neat table
        print "New session started."
        table = [["Username", username],
                 ["Student Number", studentNum],
                 ["Session ID", sessionId],
                 ["timetableUrl", timetableUrl]]
        out = sys.stdout
        pprint_table(out, table)
        print ""

        processEnrolmentLink = None
        try:
            while not processEnrolmentLink:
                print "Attempting to find enrolment link..."
                processEnrolmentLink = getProcessEnrolmentLink(timetableUrl, tut_string)
        except SessionExpiredError, e:
            print "Session expired."
            continue
    print "\nEnrolment link found: %s" % processEnrolmentLink
    print "Attempting to enrol..."

    fd = urllib2.urlopen(processEnrolmentLink)
    for line in fd:
        if re.search("successfully Enrolled", line):
            print "Enrolment was successful"
            return
    print "Error: Enrolment was not successful"
__main__()
