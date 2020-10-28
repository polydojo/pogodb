"""
PogoDB: Simple NoSQL wrapper for Postgres' JSONB type.

Copyright (c) 2020 Polydojo, Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
""";

import pprint;
import functools;
import json;
import contextlib;

import psycopg2;
import psycopg2.extras;
import dotsi;

__version__ = "0.0.1";  # Req'd by flit.
mapli = lambda seq, fn: dotsi.List(map(fn, seq));

# Good to know:
# With cursor_factory=psycopg2.extras.RealDictCursor,
#   cursor.fetchone() returns an instance of RealDictRow.
#   And cursor.fetchall() returns a list thereof.
#


def bindConCur (con, cur):
    db = dotsi.fy({"_con": con, "_cur": cur});  # Mainatain ref.

    def execute (stmt, args=None, fetch=None):
        cur.execute(stmt, args);
        if fetch in ["one", 1]:
            # cur.fetchone() -> psycopg2.extras.RealDictRow
            return dotsi.Dict(cur.fetchone());
        if fetch == "all":
            # cur.fetchall -> list of psycopg2.extras.RealDictRow
            return mapli(cur.fetchall(), dotsi.Dict);
        return None;
    db.execute = execute;
    
    def ensureTable ():
        stmtList = [
            """
            CREATE TABLE IF NOT EXISTS pogotbl (
                doc JSONB NOT NULL,
                CONSTRAINT _id_str_ CHECK (
                    (doc->'_id') IS NOT NULL
                        AND
                    jsonb_typeof(doc->'_id') = 'string'
                )
            );
            """,
            "CREATE UNIQUE INDEX IF NOT EXISTS _id_unq ON pogotbl ((doc->'_id'));",
        ];
        for stmt in stmtList:
            execute(stmt);
        return None;
    db.ensureTable = ensureTable;
    
    def showTables ():
        stmt = "SELECT * FROM pg_catalog.pg_tables WHERE schemaname != 'pg_catalog' AND schemaname != 'information_schema';";
        pprint.pprint(execute(stmt, fetch="all"));
    db.showTables = showTables;
    
    def dropTable ():
        stmt = "DROP TABLE IF EXISTS pogotbl;";
        execute(stmt);
    db.dropTable = dropTable;
    
    def clearTable ():
        dropTable();
        ensureTable();
    db.clearTable = clearTable;
        
    def insertOne (doc):
        doc = dotsi.fy(doc);
        stmt = "INSERT INTO pogotbl (doc) VALUES (%s);";
        execute(stmt, [json.dumps(doc)]);
    db.insertOne = insertOne;
    db.insertMany = lambda docList: mapli(docList, insertOne);
    
    def replaceOne (doc):
        doc = dotsi.fy(doc);
        stmt = "UPDATE pogotbl SET doc = %s WHERE doc->>'_id' = %s";
        execute(stmt, [json.dumps(doc), doc._id]);
    db.replaceOne = replaceOne;
    db.replaceMany = lambda docList: mapli(docList, replaceOne);
    
    def deleteOne (docId):
        stmt = "DELETE FROM pogotbl WHERE doc->>'_id' = %s";
        execute(stmt, [docId]);
    db.deleteOne = deleteOne;
    
    def findSql (sql, args=None):
        return mapli(
            execute(sql, args, fetch="all"),
            lambda record: record["doc"],
        );
    db.findSql = findSql;

    def find (subdoc, whereEtc="", argsEtc=None, limit=None):
        # Checks:
        assert isinstance(subdoc, dict) or type(subdoc) is str;
        assert type(whereEtc) is str;
        assert argsEtc is None or type(argsEtc) is list;
        assert limit is None or (type(limit) is int and limit > 0);
        # Compose:
        stmt = "\n".join([
            "SELECT doc FROM pogotbl WHERE doc @> %s",
            whereEtc,
            "LIMIT %s" if limit else "",
            ";",
        ]);
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
        docList = findSql("SELECT doc FROM pogotbl WHERE doc->>'_id' = %s", [_id]);
        assert len(docList) <= 1;
        return None if not docList else dotsi.fy(docList[0]);
    db.findById = findById;
    
    def findOne (subdoc, whereEtc="", argsEtc=None):
        if type(subdoc) is str:
            return findById(subdoc);
        docList = find(subdoc, whereEtc, argsEtc, limit=1);
        assert len(docList) <= 1;
        return None if not docList else docList[0];
    db.findOne = findOne;
    
    def incr (subdoc, keyPath, delta):
        if type(subdoc) is str: subdoc = {"_id": subdoc};
        stmt = "UPDATE pogotbl SET doc = jsonb_set(doc, %s, ((doc #> %s)::int + %s)::text::jsonb) WHERE doc @> %s;";
        args = [keyPath, keyPath,  delta,  json.dumps(subdoc)];
        execute(stmt, args);
    db.incr = incr;
    
    def decr (subdoc, keyPath, delta):
        return incr(subdoc, keyPath, -delta);
    db.decr = decr;
    
    def push (subdoc, arrPath, newEl):                      # arrPath: path to array. lastElPath: path to last element _in_ array. 
        if type(subdoc) is str: subdoc = {"_id": subdoc};
        lastElPath = arrPath + ["-1"];
        stmt = "UPDATE pogotbl SET doc = jsonb_insert(doc, %s, %s, true) WHERE doc @> %s;";
        args = [lastElPath, json.dumps(newEl), json.dumps(subdoc)];
        execute(stmt, args);
    db.push = push;
    
    # Return built `db`.
    db.ensureTable();   # TODO: Make this skippable.
    return db;

@contextlib.contextmanager
def connect (pgUrl):
    "Returns a context-managed `db`, bound to `pgUrl`.";
    con = psycopg2.connect(pgUrl);
    with con:
        cur = con.cursor(cursor_factory=psycopg2.extras.RealDictCursor);
        with cur:
            db = bindConCur(con, cur);
            yield db;
    #TMP: try: con.close(); except: pass; assert con.closed;
    con.close();    # Close _OUTSIDE_ the `with con` block;
    assert con.closed;
    return None;

def makeConnector (pgUrl):
    "Returns a `db`-supplying decorator, bound to `pgUrl`.";
    def dbConnector (fn):
        @functools.wraps(fn)
        def wrapper (*args, **kwargs):
            with connect(pgUrl) as db:
                return fn(db=db, *args, **kwargs);
        return wrapper;
    return dbConnector;

def shellConnect (pgUrl):
    "Returns context-unmanaged `db`, for use in Python Shell.";
    db = dotsi.fy({});  # Start empty, maintain reference.
    def reopen (msg="Connection re-opened. Call `.close()` to close."):
        con = psycopg2.connect(pgUrl);
        cur = con.cursor(cursor_factory=psycopg2.extras.RealDictCursor);
        db.update(bindConCur(con, cur));
        if msg: print(msg);
    db.reopen = reopen;
    def close (msg="Connection committed & closed. Call `.reopen()` to resume."):
        db._cur.close();
        db._con.commit();
        db._con.close();
        if msg: print(msg);
    db.close = close;
    # Open (1st time) and return:
    db.reopen("Connection opened. Call `.close()` to close.");
    return db;

# End ######################################################
