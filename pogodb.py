"""
PogoDB: Simple NoSQL wrapper around Postgres' JSONB type.

Copyright (c) 2020 Polydojo, Inc.

SOFTWARE LICENSING
------------------
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

NO TRADEMARK RIGHTS
-------------------
The above software licensing terms DO NOT grant any right in the
trademarks, service marks, brand names or logos of Polydojo, Inc.
""";

import pprint;
import functools;
import json;
import contextlib;

import dotsi;
try:
    import psycopg2;
except ImportError as e:
    raise ImportError(
        "No module named 'psycopg2'. Please install "
        "psycopg2 OR psycopg2-binary to resolve this issue. "
        "Installation via pip is recommended."
    );
import psycopg2.extras;

__version__ = "0.0.3";  # Req'd by flit.

mapli = lambda seq, fn: dotsi.List(map(fn, seq));

# Good to know:
# With cursor_factory=psycopg2.extras.RealDictCursor,
#   cursor.fetchone() returns an instance of RealDictRow.
#   And cursor.fetchall() returns a list thereof.
#

#TODO/consider: Remove excess dotsi.fy(.) calls. Or not?


def bindConCur (con, cur, skipSetup=False, verbose=False):
    db = dotsi.fy({"_con": con, "_cur": cur});  # Mainatain ref.

    def execute (stmt, args=None, fetch=None):
        "Run SQL `stmt` by substituting `args`, then `fetch`.";
        if verbose:
            print("\nExecuting SQL:");
            print("`" * 60);
            print(cur.mogrify(stmt, args).decode(db._con.encoding));
            # Or .decode()
            print("`" * 60);
        if fetch not in [None, "one", 1, "all"]:
            raise ValueError("Unexpected `fetch` argument: %s" % (fetch,));
        cur.execute(stmt, args);
        if fetch in ["one", 1]:
            # cur.fetchone() -> psycopg2.extras.RealDictRow
            return dotsi.Dict(cur.fetchone());
        if fetch == "all":
            # cur.fetchall -> list of psycopg2.extras.RealDictRow
            return mapli(cur.fetchall(), dotsi.Dict);
        assert fetch is None;
        return None;
    db._execute = execute;
    
    def ensureTable ():
        "Ensures that table 'pogotbl' is set up properly.";
        stmtList = [
            # First statement:
            "CREATE TABLE IF NOT EXISTS pogotbl (           \n"
            "    doc JSONB NOT NULL,                        \n"
            "    CONSTRAINT _id_str_ CHECK (                \n"
            "        (doc->'_id') IS NOT NULL               \n"
            "            AND                                \n"
            "        jsonb_typeof(doc->'_id') = 'string'    \n"
            "    )                                          \n"
            ");                                             ",
            # Second statement:
            "CREATE UNIQUE INDEX IF NOT EXISTS _id_unq ON pogotbl ((doc->'_id'));",
        ];
        for stmt in stmtList:
            execute(stmt);
        return None;
    db.ensureTable = ensureTable;
    
    def showTables ():
        "Utility. Shows non-default tables in the Postgres database.";
        stmt = "SELECT * FROM pg_catalog.pg_tables WHERE schemaname != 'pg_catalog' AND schemaname != 'information_schema';";
        pprint.pprint(execute(stmt, fetch="all"));
    db.showTables = showTables;
    
    def dropTable (sure=False):
        "Drops the 'pogotbl' table.";
        if sure is not True:
            raise ValueError("dropTable:: Are you sure? Pass `sure=True` if you really are.");
        stmt = "DROP TABLE IF EXISTS pogotbl;";
        execute(stmt);
    db.dropTable = dropTable;
    
    def clearTable (sure=False):
        "Clears the 'pogotbl' table.";
        if sure is not True:
            raise ValueError("clearTable:: Are you sure? Pass `sure=True` if you really are.");
        dropTable(sure);
        ensureTable();
    db.clearTable = clearTable;
        
    def insertOne (doc):
        "Inserts a single document, `doc`.";
        doc = dotsi.fy(doc);
        stmt = "INSERT INTO pogotbl (doc) VALUES (%s);";
        execute(stmt, [json.dumps(doc)]);
    db.insertOne = insertOne;
    db.insertMany = lambda docList: mapli(docList, insertOne);
    
    def replaceOne (doc):
        "Overwrites document `doc`, via `doc['_id'].";
        doc = dotsi.fy(doc);
        stmt = "UPDATE pogotbl SET doc = %s WHERE doc->>'_id' = %s;";
        execute(stmt, [json.dumps(doc), doc._id]);
    db.replaceOne = replaceOne;
    db.replaceMany = lambda docList: mapli(docList, replaceOne);
    
    def deleteOne (_id):
        "Deletes a single document by it's `_id`.";
        stmt = "DELETE FROM pogotbl WHERE doc->>'_id' = %s;";
        execute(stmt, [_id]);
    db.deleteOne = deleteOne;
    
    def findSql (stmt, args=None):
        return mapli(
            execute(stmt, args, fetch="all"),
            lambda record: record["doc"],
        );
    db._findSql = findSql;

    def find (subdoc, whereEtc="", argsEtc=None, limit=None):
        # Checks:
        assert isinstance(subdoc, dict);
        assert type(whereEtc) is str;
        if whereEtc.strip():
            assert whereEtc.split()[0].upper() != "WHERE";
        assert argsEtc is None or type(argsEtc) is list;
        assert limit is None or (type(limit) is int and limit > 0);
        # Compose:
        stmt = "\n".join(filter(str.strip, [
            "SELECT doc FROM pogotbl WHERE doc @> %s",
            whereEtc,
            "LIMIT %s" if limit else "",
        ])) + ";";
        args = (
            [json.dumps(subdoc)] +
            (argsEtc or []) +
            ([limit] if limit else []) #+
        );
        # Execute:
        return findSql(stmt, args);
    db.find = find;
            
    def findById (_id):
        assert type(_id) is str;
        docList = findSql("SELECT doc FROM pogotbl WHERE doc->>'_id' = %s;", [_id]);
        assert len(docList) <= 1;
        return None if not docList else dotsi.fy(docList[0]);
    db.findById = findById;
    
    def findOne (subdoc, whereEtc="", argsEtc=None):
        if (type(subdoc) is str) and (whereEtc == "") and (argsEtc is None):
            return findById(subdoc);
        docList = find(subdoc, whereEtc, argsEtc, limit=1);
        assert len(docList) <= 1;
        return None if not docList else docList[0];
    db.findOne = findOne;
    
    def incr (subdoc, keyPath, delta):
        if type(subdoc) is str:
            subdoc = {"_id": subdoc};
        if type(keyPath) is str:
            keyPath = keyPath.split(".");
        stmt = "UPDATE pogotbl SET doc = jsonb_set(doc, %s, ((doc #> %s)::int + %s)::text::jsonb) WHERE doc @> %s;";
        args = [keyPath, keyPath,  delta,  json.dumps(subdoc)];
        execute(stmt, args);
    db.incr = incr;
    
    def decr (subdoc, keyPath, delta):
        return incr(subdoc, keyPath, -delta);
    db.decr = decr;
    
    def push (subdoc, arrPath, newEl):
        "Push `newEl` after `arrPath` in documents matching `subdoc`.";
        # arrPath: path to array.
        # lastElPath: path to last element _in_ array. 
        if type(subdoc) is str:
            subdoc = {"_id": subdoc};
        if type(arrPath) is str:
            arrPath = arrPath.split(".");
        lastElPath = arrPath + ["-1"];
        stmt = "UPDATE pogotbl SET doc = jsonb_insert(doc, %s, %s, true) WHERE doc @> %s;";
        args = [lastElPath, json.dumps(newEl), json.dumps(subdoc)];
        execute(stmt, args);
    db.push = push;
    
    # Return built `db` (after setting up pogotbl.)
    if not skipSetup:
        db.ensureTable();
    db.update({"_skippedSetup": skipSetup, "_ranSetup": not skipSetup});
    return db;

@contextlib.contextmanager
def connect (pgUrl, skipSetup=False, verbose=False):
    "Returns a context-managed `db`, bound to `pgUrl`.";
    if verbose: print("Connecting to Postgres ...");
    con = psycopg2.connect(pgUrl);
    with con:
        cur = con.cursor(cursor_factory=psycopg2.extras.RealDictCursor);
        with cur:
            db = bindConCur(con, cur, skipSetup, verbose);
            yield db;
    #TMP: try: con.close(); except: pass; assert con.closed;
    con.close();    # Close _OUTSIDE_ the `with con` block;
    assert con.closed;
    if verbose: print("Postgres connection closed.");
    return None;

def makeConnector (pgUrl, skipSetup=False, verbose=False):
    "Returns a `db`-supplying decorator, bound to `pgUrl`.";
    ref = dotsi.fy({"skip1st": skipSetup, "used1st": False});
    def dbConnector (fn):
        @functools.wraps(fn)
        def wrapper (*args, **kwargs):
            if not ref.used1st:
                shouldSkip = ref.skip1st;
                ref.used1st = not ref.used1st;
            else:
                shouldSkip = True;
            with connect(pgUrl, shouldSkip, verbose) as db:
                # TODO: Allow custom param name, instead of just `db`.
                return fn(db=db, *args, **kwargs);
        return wrapper;
    return dbConnector;

def shellConnect (pgUrl, verbose=False):
    "Returns context-unmanaged `db`, for use in Python Shell.";
    db = dotsi.fy({});  # Start empty, maintain reference.

    nl = lambda s: "\n" + s + "\n" if verbose else s;   # New Line wrapper
    MSG_OPN = nl("Connection opened. Call `.close()` to close.");
    MSG_CLS = nl("Connection committed & closed. Call `.reopen()` to resume.");
    MSG_RPN = nl("Connection re-opened. Call `.close()` to close.");

    def reopen (msg=MSG_RPN, skipSetup=True):
        con = psycopg2.connect(pgUrl);
        cur = con.cursor(cursor_factory=psycopg2.extras.RealDictCursor);
        db.update(bindConCur(con, cur, skipSetup, verbose));
        if msg: print(msg);
    db.reopen = reopen;

    def close (msg=MSG_CLS):
        db._cur.close();
        db._con.commit();
        db._con.close();
        if msg: print(msg);
    db.close = close;

    # Open (1st time) and return:
    db.reopen(MSG_OPN, skipSetup=False);
    return db;

# End ######################################################
