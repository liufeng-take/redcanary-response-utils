#!/usr/bin/env python

import argparse
import csv
import os
import sys
from datetime import datetime

# Red Canary
from common import *

# Carbon Black
from cbapi.response import CbEnterpriseResponseAPI
from cbapi.response.models import Process, Sensor
from cbapi.errors import *


if sys.version_info.major >= 3:
    _python3 = True
else:
    _python3 = False


def process_search(cb_conn, query, query_base=None,
                   filemods=None, netconns=None, 
                   processes=None, regmods=None):

    if query_base != None:
        query += query_base

    log_info("QUERY: {0}".format(query))

    query_result = cb_conn.select(Process).where(query).group_by("id")
    query_result_len = len(query_result)
    log_info('Total results: {0}'.format(query_result_len))

    results = []

    try:
        process_counter = 0
        for proc in query_result:
            process_counter += 1
            if process_counter % 10 == 0:
                log_info('Processing {0} of {1}'.format(process_counter, query_result_len))

            hostname = proc.hostname.lower()
            username = proc.username.lower()
            path = proc.path
            cmdline = proc.cmdline

            try:
                process_md5 = path.process_md5
            except:
                process_md5 = ''

            parent_name = proc.parent_name

            if processes == True:
                results.append(('process',
                                convert_timestamp(proc.start),
                                hostname,
                                username,
                                path,
                                cmdline,
                                process_md5,
                                parent_name,
                                proc.childproc_count,
                                proc.webui_link
                                ))

            if netconns == True:
                for netconn in proc.all_netconns():
                    results.append(('netconn',
                                    convert_timestamp(netconn.timestamp),
                                    hostname,
                                    username,
                                    path,
                                    cmdline,
                                    process_md5,
                                    parent_name,
                                    proc.childproc_count,
                                    proc.webui_link,
                                    netconn.domain,
                                    netconn.remote_ip,
                                    netconn.remote_port,
                                    netconn.local_ip,
                                    netconn.local_port,
                                    netconn.proto,
                                    netconn.direction
                                    ))

            if filemods == True:
                for filemod in proc.all_filemods():
                    results.append(('filemod',
                                    convert_timestamp(filemod.timestamp),
                                    hostname,
                                    username,
                                    path,
                                    cmdline,
                                    process_md5,
                                    parent_name,
                                    proc.childproc_count,
                                    proc.webui_link,
                                    '','','','','','','', # netconn
                                    filemod.path,
                                    filemod.type,
                                    filemod.md5
                                    ))

            if regmods == True:
                for regmod in proc.all_regmods():
                    results.append(('regmod',
                                    convert_timestamp(regmod.timestamp),
                                    hostname,
                                    username,
                                    path,
                                    cmdline,
                                    process_md5,
                                    parent_name,
                                    proc.childproc_count,
                                    proc.webui_link,
                                    '','','','','','','',   # netconn
                                    '','','',               # filemod
                                    regmod.path,
                                    regmod.type
                                    ))


    except KeyboardInterrupt:
        log_info("Caught CTRL-C. Returning what we have . . .")

    return results


def main():
    parser = build_cli_parser("Timeline utility")

    # Output options
    output_events = parser.add_argument_group('output_events', 
        "If any output type is set, all other types will be suppressed unless they are explicitly set as well.")
    output_events.add_argument("--filemods", action="store_true",
                        help="Output file modification records.")
    output_events.add_argument("--netconns", action="store_true",
                        help="Output network connection records.")
    output_events.add_argument("--processes", action="store_true",
                        help="Output process start records.")
    output_events.add_argument("--regmods", action="store_true",
                        help="Output registry modification records.")

    args = parser.parse_args()

    if args.prefix:
        filename = '{0}-timeline.csv'.format(args.prefix)
    else:
        filename = 'timeline.csv'

    if args.append == True or args.queryfile is not None:
        file_mode = 'a'
    else:
        file_mode = 'w'

    if args.days:
        query_base = ' start:-{0}m'.format(args.days*1440)
    elif args.minutes:
        query_base = ' start:-{0}m'.format(args.minutes)
    else:
        query_base = ''

    # This is horrible. All are False by default. If all are False, then set
    # all to True. If any are set to True, then evaluate each independently.
    # If you're reading this and know of a cleaner way to do this, ideally via
    # argparse foolery, by all means . . .
    if args.filemods == False and \
       args.netconns == False and \
       args.processes == False and \
       args.regmods == False:
        (filemods, netconns, processes, regmods) = (True, True, True, True)
    else:
        filemods = args.filemods
        netconns = args.netconns
        processes = args.processes
        regmods = args.regmods

    if args.profile:
        cb = CbEnterpriseResponseAPI(profile=args.profile)
    else:
        cb = CbEnterpriseResponseAPI()

    queries = []
    if args.query:
        queries.append(args.query)
    elif args.queryfile:
        with open(args.queryfile, 'r') as f:
            for query in f.readlines():
                queries.append(query.strip())
        f.close()
    else:
        queries.append('')

    file = open(filename, file_mode)
    writer = csv.writer(file)
    writer.writerow(["event_type",
                     "timestamp",
                     "hostname",
                     "username",
                     "path",
                     "cmdline",
                     "process_md5",
                     "parent",
                     "childproc_count",
                     "url",
                     "netconn_domain",
                     "netconn_remote_ip",
                     "netconn_remote_port",
                     "netconn_local_ip",
                     "netconn_local_port",
                     "netconn_proto",
                     "netconn_direction",
                     "filemod_path",
                     "filemod_type",
                     "filemod_md5",
                     "regmod_path",
                     "regmod_type"
                     ])

    for query in queries:
        result_set = process_search(cb, query, query_base, filemods, netconns,
                                    processes, regmods)

        for row in result_set:
            if _python3 == False:
                row = [col.encode('utf8') if isinstance(col, unicode) else col for col in row]
            writer.writerow(row)

    file.close()


if __name__ == '__main__':

    sys.exit(main())
