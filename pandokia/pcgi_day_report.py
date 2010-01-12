#
# pandokia - a test reporting and execution system
# Copyright 2009, Association of Universities for Research in Astronomy (AURA) 
#

#
import sys
import cgi
import re
import copy
import time

import pandokia.text_table as text_table
import urllib

import pandokia
import pandokia.common as common

import pandokia.pcgi

######
#
# day_report.1
#   show a list of test_run values that we can make a day_report for
#
# CGI parameters:
#   test_run = wild card pattern for test_run
#

def rpt1(  ) :

    db = common.open_db()

    form = pandokia.pcgi.form

    if form.has_key("test_run") :
        test_run = form["test_run"].value
        if test_run == '-me' :
            test_run = 'user_' + common.current_user() + '_*'
        c = db.execute("SELECT DISTINCT test_run FROM result_scalar WHERE test_run GLOB ? ORDER BY test_run DESC ",( test_run,))
    else :
        # GLOB '*' is not nearly as fast as leaving out the GLOB.
        c = db.execute("SELECT DISTINCT test_run FROM result_scalar ORDER BY test_run DESC ")

    table = text_table.text_table()

    # day report, tree walk, problem list
    dquery = { }
    lquery = { 'project' : '*', 'host' : '*', 'status' : '[FE]' }
    tquery = { 'project' : '*', 'host' : '*' }

    row = 0
    for x in c :
        (x,) = x
        if x is None :
            continue
        dquery["test_run"] = x
        lquery["test_run"] = x
        tquery["test_run"] = x

        table.set_value(row, 0, text=x, link=common.selflink(dquery,"day_report.2") )
        table.set_value(row, 2, text='(tree display)', link=common.selflink(tquery,"treewalk") )
        table.set_value(row, 3, text='(problem tests)', link=common.selflink(lquery,"treewalk.linkout") )
        row = row + 1

    if pandokia.pcgi.output_format == 'html' :
        sys.stdout.write(common.cgi_header_html)
        sys.stdout.write('<h2>%s</h2>'%cgi.escape(test_run))
        sys.stdout.write(table.get_html(headings=1))
    elif pandokia.pcgi.output_format == 'csv' :
        sys.stdout.write(common.cgi_header_csv)
        sys.stdout.write(table.get_csv())

    return

######
#
# day_report.2
#   show the actual day report: 
#       for each project show a table containing pass/fail/error for each host
#
# parameters:
#   test_run = name of test run to show data for
#       no wild cards permitted, but we allow special names
#

def rpt2( ) :

    db = common.open_db()

    form = pandokia.pcgi.form

    if form.has_key("test_run") :
        test_run = form["test_run"].value
    else :
        # no parameter?  I think somebody is messing with us...
        # no matter - just give them a the list of all the test_runs
        rpt1()
        return

    # convert special names, e.g. daily_latest to the name of the latest daily_*
    test_run = common.find_test_run(test_run)

    # create list of projects
    projects = [  ]
    c = db.execute("SELECT DISTINCT project FROM result_scalar WHERE test_run = ? ORDER BY project ", (test_run, ) )
    for x in c :
        (x,) = x
        if x is None :
            continue
        projects.append(x)

    # this is the skeleton of the cgi queries for various links
    query = { "test_run" : test_run }

    # This is a single table for all projects, because we want the
    # pass/fail/error columns to be aligned from one to the next
    #
    table = text_table.text_table()

    # The texttable object doesn't understand colspans, but we hack a
    # colspan into it anyway.  Thee result is ugly if you have borders.

    table.set_html_table_attributes("cellpadding=2")

    row = 0
    table.define_column("host")
    table.define_column("os")
    table.define_column("total")
    table.define_column("pass")
    table.define_column("fail")
    table.define_column("error")
    table.define_column("disabled")
    table.define_column("missing")
    table.define_column("note")

#   #   #   #   #   #   #   #   #   #
    for p in projects :

        # values common to all the links we will write in this pass through the loop
        query["project"] = p
        query["host"] = "*"

        # this link text is common to all the links for this project
        link = common.selflink(query_dict = query, linkmode="treewalk" )

        # the heading for a project subsection of the table
        table.set_value(row, 0, text=p, html="<big><strong><b>"+p+"</b></strong></big>", link=link)
        table.set_html_cell_attributes(row,0,"colspan=8")
        row += 1

        # the column headings for this project's part of the table
        table.set_value(row, "total", text="total", link=link )
        table.set_value(row, "pass", text="pass", link=link+"&status=P")
        table.set_value(row, "fail", text="fail", link=link+"&status=F")
        table.set_value(row, "error", text="error", link=link+"&status=E")
        table.set_value(row, "disabled", text="disabled", link=link+"&status=D")
        table.set_value(row, "missing", text="missing", link=link+"&status=M")
        table.set_value(row, "note", text="" )  # no heading for this one
        row += 1

        # loop across hosts
        c = db.execute("SELECT DISTINCT host FROM result_scalar WHERE test_run = ? AND project = ?", (test_run, p))
        for host in c :
            (host,) = host
            query["host"] = host
            link = common.selflink(query_dict = query, linkmode="treewalk" )
            table.set_value(row,0,    text=host,        link=link)
            table.set_value(row,1,    text=pandokia.cfg.os_info.get(host,'?') )
            col = 3  # the first column of the pass/fail/error numbers
            total_results = 0
            for status in [ 'P', 'F', 'E', 'D', 'M' ] :
                c1 = db.execute("SELECT COUNT(*) FROM result_scalar WHERE  test_run = ? AND project = ? AND host = ? AND status = ?",
                    ( test_run, p, host, status ) )
                (x,) = c1.fetchone()
                total_results = total_results + x
                table.set_value(row, col, text=str(x), link = link + "&rstatus="+status )
                col = col + 1

            if x == total_results :
                # x is the value from the _last_ column, which is 'missing'
                # if it equals the total, then everything is missing; we make a note of that
                table.set_value(row, 'note', 'all')
            elif x != 0 :
                # x is the value from the _last_ column, which is 'missing'
                # if it is not 0, then we have a problem
                table.set_value(row, 'note', 'some')

            table.set_value(row, 'total', text=str(total_results), link=link )

            row = row + 1

        # insert this blank line between projects - keeps the headings away from the previous row
        table.set_value(row,0,"")
        row = row + 1

# # # # # # # # # # 
    if pandokia.pcgi.output_format == 'html' :
        header = "<h1>"+cgi.escape(test_run)+"</h1>\n"

        if test_run.startswith('daily_') :
            # 
            # If we have a daily run, create a special header.

            # show the day of the week, if we can
            try :
                import datetime
                t = test_run[len('daily_'):]
                t = t.split('-')
                t = datetime.date(int(t[0]),int(t[1]),int(t[2]))
                t = t.strftime("%A")
                header = header+ "<h2>"+str(t)+"</h2>"
            except :
                pass

            # Include links to the previous / next day's daily run.
            # It is not worth the cost of looking in the database to make sure the day that
            # we link to really exists.  It almost always does, and if it doesn't, the user
            # will find out soon enough.
            # 

            prev = common.previous_daily( test_run )
            back = common.self_href( query_dict = {  'test_run' : prev } , linkmode='day_report.2', text=prev )
            header = header + '( prev ' + back

            latest = common.find_test_run('daily_latest') 
            if test_run != latest :
                next = common.next_daily( test_run )
                header = header + " / next " + common.self_href( query_dict={  'test_run' : next } , linkmode='day_report.2', text=next )
                if next != latest :
                    header = header + " / latest " + common.self_href( query_dict={  'test_run' : latest } , linkmode='day_report.2', text=latest )

            header = header + ' )<p>\n'

        sys.stdout.write(common.cgi_header_html)
        sys.stdout.write(header)
        sys.stdout.write(table.get_html(headings=0))
    elif pandokia.pcgi.output_format == 'csv' :
        sys.stdout.write(common.cgi_header_csv)
        sys.stdout.write(table.get_csv())


#   #   #   #   #   #   #   #   #   #
