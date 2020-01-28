# -*- coding: utf-8 -*-
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#  Created on 28 Jan 2020
#
#  @author: rhamilton

"""One line description of module.

Further description.
"""

from __future__ import division, print_function, absolute_import

from collections import OrderedDict
from datetime import datetime as dt

from influxdb import DataFrameClient


def queryConstructor(db, dtime=48, debug=False):
    """
    db is type databaseQuery, which includes databaseConfig as
    dbinfo.db.  More info in 'confHerder'.

    dtime is time from present (in hours) to query back

    Allows grouping of the results by a SINGLE tag with multiple values.

    No checking if you want all values for a given tag, so be explicit for now.
    """
    if isinstance(dtime, str):
        try:
            dtime = int(dtime)
        except ValueError:
            print("Can't convert %s to int!" % (dtime))
            dtime = 1

    if db.database.type.lower() == 'influxdb':
        if debug is True:
            print("Searching for %s in %s.%s on %s:%s" % (db.fields,
                                                          db.tablename,
                                                          db.metricname,
                                                          db.database.host,
                                                          db.database.port))

        # Some renames since this was adapted from an earlier version
        tagnames = db.tagnames
        if tagnames is not None:
            tagvals = db.tagvals
        else:
            tagvals = []

        # TODO: Someone should write a query validator to make sure
        #   this can't run amok.  For now, make sure the user has
        #   only READ ONLY privileges to the database in question!!!
        query = 'SELECT'
        if isinstance(db.fields, list):
            for i, each in enumerate(db.fields):
                # Catch possible fn/dn mismatch
                try:
                    query += ' "%s" AS "%s"' % (each.strip(),
                                                db.fieldlabels[i])
                except IndexError:
                    query += ' "%s"' % (each.strip())
                if i != len(db.fields)-1:
                    query += ','
                else:
                    query += ' '
        else:
            if db.fieldlabels is not None:
                query += ' "%s" AS "%s" ' % (db.fields, db.fieldlabels)
            else:
                query += ' "%s" ' % (db.fields)

        query += 'FROM "%s"' % (db.metricname)
        query += ' WHERE time > now() - %02dh' % (dtime)

        if tagvals != []:
            query += ' AND ('
            if isinstance(db.tagvals, list):
                for i, each in enumerate(tagvals):
                    query += '"%s"=\'%s\'' % (tagnames, each.strip())

                    if i != len(tagvals)-1:
                        query += ' OR '
                query += ') GROUP BY "%s"' % (tagnames)
            else:
                # If we're here, there was only 1 tag value so we don't need
                #   to GROUP BY anything
                query += '"%s"=\'%s\')' % (tagnames, tagvals)

        return query


def getResultsDataFrame(host, querystr, port=8086,
                        dbuser='rand', dbpass='pass',
                        dbname='DBname'):
    """
    Attempts to distinguish queries that have results grouped by a tag
    vs. those which are just of multiple fields. May be buggy still.
    """
    idfc = DataFrameClient(host, port, dbuser, dbpass, dbname)

    results = idfc.query(querystr)

    betterResults = {}
    # results is a dict of dataframes, but it's a goddamn mess. Clean it up.
    for rkey in results.keys():
        # If you had a tag that you "GROUP BY" in the query, you'll now have
        #   a tuple of the metric name and the tag + value pair. If you had
        #   no tag to group by, you'll have just the flat result.
        if isinstance(rkey, tuple):
            # Someone tell me again why Pandas is so great?
            #   I suppose it could be jankiness in influxdb-python?
            #   This magic 'tval' line below is seriously dumb though.
            tval = rkey[1][0][1]
            dat = results[rkey]
            betterResults.update({tval: dat})
        elif isinstance(rkey, str):
            betterResults = results[rkey]

    # This is at least a little better
    return betterResults


def batchQuery(quer, debug=False):
    """
    It's important to do all of these queries en-masse, otherwise the results
    could end up being confusing - one set of data could differ by
    one (or several) update cycle times eventually, and that could be super
    confusing when it's really just our view of the state has drifted.
    """
    qdata = OrderedDict()

    for iq in quer.keys():
        q = quer[iq]

        # Should not only pull this out of the loop, but change it to
        #   use 'bind_params' for extra safety!
        query = queryConstructor(q, dtime=q.rangehours, debug=debug)

        td = getResultsDataFrame(q.database.host, query,
                                 q.database.port,
                                 dbuser=q.database.user,
                                 dbpass=q.database.password,
                                 dbname=q.tablename)
        qdata.update({iq: td})

    dts = dt.utcnow()
    print("%d queries complete!" % (len(qdata)))

    print("Data stored at %s" % (dts))
