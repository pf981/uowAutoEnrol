#!/usr/bin/python
# #!/bin/python # Use this for Solaris (Banshee)
"""
This script will automatically enrol a student in a given tutorial at the correct time by sending
POST data to sols.

POST data was manually observed using Firefox with the Tamper Data extension.

Note that is seems that when a session modifies information on Sols' database, it will invalidate
all other sessions.

Testing cannot really be done until enrolment opens...
"""

__version__ = "0.1.0"
__author__ = "Paul Foster"
__date__ = "12-02-2012"

import sys, urllib2, urllib, re
from optparse import OptionParser
import HTMLParser

from padnums import pprint_table

# from lxml.html import fromstring, tostring # perhaps lxml.html could be installed and used for parsing forms to get the p_cs variables (and the others actually...)

parser = OptionParser()
parser.add_option("-u", "--username", dest="username",
                  help="UOW SOLs username login (mandatory)", metavar="USERNAME")
parser.add_option("-p", "--password", dest="password",
                  help="UOW SOLs password login (mandatory)", metavar="PASSWORD")
(opts, args) = parser.parse_args()

mandatories = ['username', 'password']
for m in mandatories:
    if not opts.__dict__[m]:
        print "mandatory option is missing\n"
        parser.print_help()
        exit(-1)
username = opts.username
password = opts.password


def setupUowProxy():
    "Setup uow proxy with credentials (Don't need to do this because it is a local UOW site)"
    urllib2.install_opener(
        urllib2.build_opener(
            urllib2.ProxyHandler({'http': "http://%s:%s@proxy.uow.edu.au:8080/" % (username, password)})
            )
        )

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
        (str, str). The session id and student number
    """
    url = 'https://solss.uow.edu.au/sid/sols_logon.validate_sols_logon'
    postData = urllib.urlencode([('p_username', username),('p_password', password)])
    fd = postAndGetReply(url, postData)

    # Find the session id in the reply
    # fixme: perhaps make a function (studentNum, sessionId) = findInReply(regex1, regex2...)
    # fixme: and figure out how to flag if there was none found. It will return when it finds them both
    while 1:
        data = fd.read(1024) # fixme: it is possible that this will read in half of the student number - that would result in trouble
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

# fixme: remove
# This is a test function
# Deactivates IMB's access to my enrolment record
def deactivateImbEnrolmentRecord(sessionId, studentNum, cs2):
    url = 'https://solss.uow.edu.au/sid/print_enrolment_record_std.maintain_profile'
    postData = urllib.urlencode([('p_verification_profile_id', '66035'),('p_stdnbr', studentNum),('p_session_id',sessionId),('p_db_session_id',''),('p_cs',cs2),('p_submit','Deactivate')])

    req = urllib2.Request(url)
    req.add_header("Content-type", "application/x-www-form-urlencoded")
    fd = urllib2.urlopen(req,postData)

    # fixme: remove
    while 1:
        data = fd.read(1024)
        if not len(data):
            break
        print data

# This is a test function
# Returns cs2. See main for description
def getCs2(sessionId, studentNum, cs1):
    url = 'https://solss.uow.edu.au/sid/print_enrolment_record_std.display_profile'
    postData = urllib.urlencode([('p_stdnbr', studentNum),('p_session_id',sessionId),('p_db_session_id',''),('p_cs',cs1)])
    req = urllib2.Request(url)
    req.add_header("Content-type", "application/x-www-form-urlencoded")
    fd = urllib2.urlopen(req,postData)

    while 1:
        data = fd.read(1024)
        if not len(data):
            sys.stderr.write("Error: could not find p_cs in print enrolment record reply data.")
            sys.exit(1)
        matchedCs2 = re.search('p_cs=([0-9]*)', data)
        if matchedCs2:
            return matchedCs2.group(1)

# fixme: WIP
def openEnrolment(sessionId, studentNum, cs1):
    """Login->Tutorial Enrolment (Main Menu) -> Continue (Button)
    Args:
        sessionId (str): The session ID to post
        studentNum (str): The student number to post
        cs1 (str): The p_cs variable obtained from the link address of items in the main menu (namely from the "Tutorial Enrolment" link of the "Print Enrolment Record" link). This will be used to post
    """

    url = 'https://solss.uow.edu.au/sid/tutorial_enrolment.display_tutorial'
    postData = urllib.urlencode([('p_student_number', studentNum),('p_session_id', sessionId),('p_cs',cs1),('p_submit','Continue')])

    fd = postAndGetReply(url, postData)

    while 1:
        data = fd.readline()
        if not len(data):
            break

        # Get the post data for the tutorial enrolment for that subject
        matchedPostData = re.search('<a href="tutorial_enrolment.display_tutorial_timetable\?(p_sub_inst_id_pri=.*?)"', data)
        if matchedPostData:
            # Get the individual times, open/close dates for the enrolment.
            getEnrolmentOptions(matchedPostData.group(1))


def parseTable(fd):
    tableToReturn = list()
    curRowContents = list()

    while True:
        line = fd.readline()
        if not len(line):
            raise NameError('Unable to parse malformed table. End of file reached before closing TABLE tag.')

        # fixme: make a helper function find(regex, line, group) where group=0 => return whole line, group could be optional, possible could return bool so bool find(regex, line, group, matchedString) and the function modifies matchedString

        if re.search('</TR>', line):
            tableToReturn.append(curRowContents) # add list to list of lists
            curRowContents = list() # clear list
            continue

        matchedCell = re.search('>(.*)<', line)
        if matchedCell:
            curRowContents.append(matchedCell.group(1)) # add to list
            continue

        if re.search('</TABLE>', line):
            break

    # fixme: remove output
    out = sys.stdout
    pprint_table(out, tableToReturn)
    return tableToReturn

def getEnrolmentOptions(postData):
    print "\nGeting enrolment options"

    fd = postAndGetReply("https://solss.uow.edu.au/sid/tutorial_enrolment.display_tutorial_timetable", postData)

    # Look for the HTML table with all the enrolment options and put it into a pretty print table
    while 1:
        line = fd.readline()
        if not len(line):
            break
        matchedSubjectName = re.search('<TITLE>.* Enrolment for (.*)</TITLE>', line)
        if matchedSubjectName:
            print matchedSubjectName.group(1)
        matchedTable = re.search('<TABLE  ALIGN="center" width="85%" class="t_b">', line)
        if matchedTable:
            parseTable(fd)

# <table  ALIGN="center" width="85%" class="t_b">


# <TABLE  ALIGN="center" width="85%" class="t_b">
# <TR  class="r" >
# <TH  class="h" align ="left" width=30%>Name</TH>
# <TH  class="h" width=35%>First Day and Time to Enrol</TH>
# <TH  class="h" width=35%>Last Day and Time to Enrol</TH>
# </TR>
# <TR  class="r" >
# <TD  class="d" width=30% align =left>AUTM-INFO411/911-CL/01</TD>
# <TD  class="d" width=35% align =center>13-Feb-2012 21:52</TD>
# <TD  class="d" width=35% align =center>11-Mar-2012 19:00</TD>
# </TR>
# </TABLE>
# <BR>
# <FORM ACTION="tutorial_enrolment.display_tutorial" METHOD="POST">
# <INPUT TYPE="hidden" NAME="p_cs" VALUE="4240557544325441413">
# <INPUT TYPE="hidden" NAME="p_student_number" VALUE="3648370">
# <INPUT TYPE="hidden" NAME="p_session_id" VALUE="HXQNVNZSLMAQBKUBEXULHDCTLVCQTUPE">
# <CENTER>
# <INPUT TYPE="submit" NAME="p_submit" VALUE="Previous" style="width:125px;"  class="btn" onmouseover="this.className='btnhov';" onmouseout="this.className='btn';" >
# </FORM>
# </CENTER>


def __main__():
    # I have no idea what p_cs is but it is needed for posting things like changes to records -
    # seems to be some sort of session id. The p_cs you get from logging in is not the one we
    # need. We need the p_cs that is from the links in the main menu.
    # They are obtained via searching for p_cs=([0-9*)
    # cs0 is obtained from the https://solss.uow.edu.au/sid/sols_logon.validate_sols_logon reply - it is unneeded
    # cs1 is obtained from the https://solss.uow.edu.au/sid/sols_menu.display_sols_menu reply - it is needed for posts to things in the main menu
    # cs2 is obtained from the printEnrolmentRecord reply - it is needed for posts activating/deactivating enrolment record copies

    (sessionId, studentNum) = startNewSession()
    cs1 = getCs1(sessionId, studentNum)
    cs2 = getCs2(sessionId, studentNum, cs1)

    # Print session information in a neat table
    print "New session started."
    table = [["Username", username],
        ["Student Number", studentNum],
        ["Session ID", sessionId],
        ["CS1", cs1],
        ["CS2", cs2]]
    out = sys.stdout
    pprint_table(out, table)

    print __date__

    # deactivateImbEnrolmentRecord(sessionId, studentNum, cs2) # fixme: This one is for testing - it is useless

    openEnrolment(sessionId, studentNum, cs1)

# This is important: The final form submit:
# <FORM ACTION="tutorial_enrolment.process_enrol" METHOD="POST">
# <INPUT TYPE="hidden" NAME="p_student_number" VALUE="3648370">
# <INPUT TYPE="hidden" NAME="p_session_id" VALUE="DCOLUIDHZKFVTUABWXTIRYFOOLBDAXJQ">
# <INPUT TYPE="hidden" NAME="p_sub_inst_id_pri" VALUE="202385">
# <INPUT TYPE="hidden" NAME="p_sub_inst_id_ori" VALUE="202385">
# <INPUT TYPE="hidden" NAME="p_tut_id" VALUE="98806">
# <INPUT TYPE="hidden" NAME="p_cs" VALUE="13565097111825023117">
# <INPUT TYPE="submit" NAME="p_submit" VALUE="Enrol Now" style="width:125px;"  class="btn" onmouseover="this.className='btnhov';" onmouseout="this.className='btn';"  id=tut_enrol  onClick="tut_enrol.disabled=true;tut_enrol.value='In Progress...';this.form.submit();">
# <INPUT TYPE="submit" NAME="p_submit" VALUE="Previous" style="width:125px;"  class="btn" onmouseover="this.className='btnhov';" onmouseout="this.className='btn';" >
# </FORM>
__main__()
    
# fixme: todo: Create a means of determining whether the session has been invalidated (ie session has been timed out)
# fixme: write unit tests
