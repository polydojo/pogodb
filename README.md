PogoDB
=======

Simple NoSQL wrapper around Postgres' JSONB type.

Installation
--------------
PogoDB is installable via pip, following a *two-step* process:
1. `pip install pogodb`
2. `pip install psycopg2` ***OR*** `pip install psycopg2-binary`

Since the `psycopg2`/`psycopg2-binary` split, instead of forcing a dependency on either one, the choice is left to you. PogoDB should work with either. *Tip:*  If `pip install psycopg2` fails, try `pip install psycopg2-binary`.

Quickstart
--------------
To connect from a Python Shell, use `pogodb.shellConnect(.)`.
```py
>>> import pogodb
>>> db = pogodb.shellConnect("postgres://..dsn..")
Connection opened. Call `.close()` to close.
>>> db.insertOne({"_id": "foo", "value": "foobar"})
>>> db.findOne("foo")
{'_id': 'foo', 'value': 'foobar'}
>>> db.close()
Connection committed & closed. Call `.reopen()` to resume.
>>>
```
*Note:* `pogodb.shellConnect(.)` is meant only for *quick and dirty* shell connections. You need to explicitly call `db.close()` to commit the transaction and close the connection.

Connecting Properly
-------------------------

**Context Manager:**

Using `with pogodb.connect(.) as db` is a better way to connect. On exiting the `with` block, the transaction is auto-committed and the connection is auto-closed.
```py
import pogodb
with pogodb.connect("postgres://..dsn..") as db:
    db.insertOne({"_id": "bar", "value": "foobar"})
    # etc. ...
```

**Connection Decorator:**
For frequently connecting to the same database, consider setting up a connection decorator as follows:
```py
import pogodb
dbConnect = pogodb.makeConnector("postgres://..dsn..")

@dbConnect
def yourLogic (db):
    db.insertOne({"_id": "baz", "value": "quax"})
    # etc. ...
```
The decorator supplies the `db` parameter to the decorated function. The parameter is supplied by name, so it must be called `db`, not `myDb` or something else. That is, `@dbConnect` automatically passes `db` to `yourLogic`, on each call.

**Parameter `skipSetup`:**  
Both `pogodb.connect(.)` and `pogodb.makeConnector(.)` accept `skipSetup` as a parameter, which defaults to `False`. By default, PogoDB runs some setup-code upon each connection.

_After_ your first interaction with the the database through  PogoDB, to _avoid_ unnecessary setup, pass `skipSetup=True`.

**Parameter `verbose`:**
Each connection method accepts `verbose` as a parameter, defaulting to `False`. If `True`, details regarding connecting to Postgres and executing SQL are printed using `print(.)`.

Inserting Data
------------------
```py
# Insert a single document:
db.insertOne({
   "_id":"a", "author":"Alice", "text":"AA", "rank":0,
})
# Insert multiple documents:
db.insertMany([
  {"_id":"b", "author":"Becci", "text":"BB", "rank":1},
  {"_id":"c", "author":"Cathy", "text":"CC", "rank":2},
  {"_id":"d", "author":"Alice", "text":"DD", "rank":1},
]);
```

**Document Model:**  
Each document must:
- be a JSON-serializable `dict` or dict-like object, *and*
- have a *unique string* value corresponding to the `"_id"` key.

Retrieving Data
-------------------
In continuation with the above code snippet ...
```py
# Find by _id:
taskA = db.findOne("a");
print(taskA.author, "-", taskA.text)
# Output: Alice - AA

# Find by sub-document:
taskB = db.findOne({"author": "Becci"});
print(taskB.author, "-", taskB.text)
# Output: Becci - BB

# Find multiple:
aliceTasks = db.find({"author": "Alice"})
assert aliceTasks[0] == taskA and len(aliceTasks) == 2
taskD = aliceTasks[1];
print(taskD.author, "-", taskD.text)
# Output: Alice - DD
```
Note: If no matching document is found, `.findOne(.)` returns `None` while `.find(.)` returns an empty list.

Updating Data
------------------
In continuation with the above code snippet ...
```py
# Replace document:
taskA.text = "New AA"           # <-- Update in-memory
taskA.x = {"y": 10, "z": 20}
db.replaceOne(taskA);           # <-- Propagate to db
print([db.findOne(taskA._id).text, taskA.x])
# Output: ['New AA', {'y': 10, 'z': 20}]

# Increment within document:
db.incr({"_id": "a"}, "x.y", 1) # Incr x.y by 1
print(db.findOne("a").x)
# Output: {'y': 11, 'z': 20}

# Decrement:
db.decr({"_id": "a"}, "x.z", 1) # Decr x.z by 1
print(db.findOne("a").x)
# Output: {'y': 11, 'z': 19}
```

Deleting Data
-----------------
In continuation with the above code snippet ...
```py
# Delete by _id:
db.deleteOne("a");
print(db.findOne("a"))
# Output: None
```
As of writing, you can only delete one document at a time, by `_id`.

Quick Plug
--------------
PogoDB built and maintained by the folks at [Polydojo, Inc.](https://www.polydojo.com/), led by Sumukh Barve. If your team is looking for a simple project management tool, please check out our latest product: [BoardBell.com](https://www.boardbell.com/).

Type Identifiers
-------------------

PogoDB doesn't include buckets, collections or other such concepts for **logically grouping** different types of objects. But you can use a key for differentiating objects of various types.

**Convention:**  
Keeping things simple, we recommend using the `"type"` key for indicating the type of a document/object.

**Example:**  
In a blogging app, you'll have to deal with users, posts, comments and other types of object. 

```py
# Insert users:
db.insertMany([
    {"_id": "00", "type":"user", "name": "Alice"},
    {"_id": "01", "type":"user", "name": "Becci"},
    {"_id": "02", "type":"user", "name": "Cathy"},
]);

# Insert posts:
db.insertMany([
    {"_id": "03", "type":"post", "authorId": "00",
        "title": "Title X .. ", "body": "Body X .."},
    {"_id": "04", "type":"post", "authorId": "01",
        "title": "Title Y .. ", "body": "Body Y .."},
    {"_id": "05", "type":"post", "authorId": "02",
        "title": "Title Z .. ", "body": "Body Z .."},
    {"_id": "06", "type":"post", "authorId": "00",
        "title": "Title A .. ", "body": "Body A .."},
]);

# Insert comments:
db.insertMany([
    {"_id": "07", "type":"comment", "authorId": "02",
        "postId": "03", "text": "Comment P .."},
    {"_id": "08", "type":"comment", "authorId": "01",
        "postId": "04", "text": "Comment Q .."},
    {"_id": "09", "type":"comment", "authorId": "00",
        "postId": "05", "text": "Comment R .."},
]);

# Get all users:
db.find({"type": "user"});

# Get all posts:
db.find({"type": "post"});

# Get posts by a specific author:
def getPostByAuthor (userId):
    return db.find({"type":"post", "authorId":userId})

# Get comments on a specific post:
def getCommentsByPost (postId):
    return db.find({"type":"comment", "postId":postId})

# Get comments by a specific user:
def getCommentsByUser (userId):
    return db.find({"type":"user", "authorId":userId})
```

As you can see, using the `"type"` key allows us to limit our query to a specific type. In continuation with the above code snippet, consider ...
```py
def typed_getPostById (postId):
    return db.findOne({"_id": postId, "type": "post"});

def untyped_getPostById (postId):
    return db.findOne({"_id": postId})

print(typed_getPostById("00"))   # Correct result.
# Output: None

print(untyped_getPostById("00")) # Weird result.
# Output: {'_id': '00', 'name': 'Alice', 'type': 'user'} 
```

In the above example, `"00"` corresponds to Alice's `"user"` object. It's not a `"post"`. Yet `untyped_getPostById(.)` (incorrectly) returns it because it is type-blind.

SQL Familiarity
-------------------

From this point, the documentation assumes basic familiarity with SQL and Postgres' JSONB type. If you aren't familiar with these, you may safely skip most of the documentation below. However, please note that such familiarity would be required for running advanced, fine-grained queries.

Under The Hood
---------------------
Under the hood, PogoDB creates a single table named `pogotbl` with a single `JSONB` column named `doc` (for document).

When you call `db.find(.)`, PogoDB uses Postgres' `@>` to find and fetch the relevant documents. For example, calling `db.find({"type": "post"})` will result in the following underlying SQL query:
```sql
SELECT doc FROM pogotbl WHERE doc @> '{"type": "post"}';
```
The above SQL will produce a list of records of type`psycopg2.extras.RealDictCursor`, each with just one column: `"doc"`. That is, the list of records is of the form:
```json
[   {"doc": {"_id": "1..", "type": "post", ...}},
    {"doc": {"_id": "2..", "type": "post", ...}},
    ...
]
```
After executing the SQL, `db.find(.)` plucks the `"doc"` column from each record and returns the resultant list, which is (as expected,) of the form:
```json
[   {"_id": "1..", "type": "post", ...},
    {"_id": "2..", "type": "post", ...},
    ...
]
```
Additionally, `db.find(.)` ensures that each returned document is a dot-accessible dictionary, thanks to [Dotsi](https://github.com/polydojo/dotsi). That is, you can use dot-notation (like `post._id`) in addition to square-bracket notation (like `post["_id"]`).

Custom `WHERE` Clause
------------------------------------

Let's say you've stored the following exam-results using PogoDB:
```json
[   {"_id":"1", "studentId":"X", "subjectId":"M", "score": 70},
    {"_id":"2", "studentId":"Y", "subjectId":"M", "score": 75},
    {"_id":"3", "studentId":"Z", "subjectId":"M", "score": 80},
    {"_id":"4", "studentId":"X", "subjectId":"N", "score": 85},
    {"_id":"5", "studentId":"Y", "subjectId":"N", "score": 90},
    {"_id":"6", "studentId":"Z", "subjectId":"N", "score": 95},
]
```

To find *all* results for *Subject M*, we'd write `db.find({"subjectId": "M"})`, which'd result in the underlying SQL query:
```sql
SELECT doc FROM pogotbl WHERE doc @> '{"subjectId": "M"}';
```

But how about retrieving ***only those*** results for *Subject M*, where the *score* is `75` or higher? In raw SQL, we could've written:
```sql
SELECT doc FROM pogotbl
  WHERE doc @> '{"subjectId": "M"}'
    AND (doc->>'score')::int >= 75;
```

With regard to the two SQL queries above, note that the `WHERE` clause additionally includes `AND (doc->>'score')::int >= 75`. You can pass this extra bit to `db.find(.)` using the `whereEtc` parameter:
```py
db.find({"subjectId": "M"},
    whereEtc="AND (doc->>'score')::int >= 75"
)
```

In fact, `db.find(.)` is very flexible. Its full signature is documented below.

Full `db.find(.)` Signature
----------------------------------

`db.find(.)` accepts 4 parameters:
1. `subdoc` (required): The sub-document to match against.
2. `whereEtc` (optional): Anything that should go ***after*** PogoDB's  default SQL `WHERE` clause.
3. `argsEtc` (optional): Tuple (or list) for placeholder-substitution against `whereEtc`.
4. `limit` (optional): The maximum number of results desired. (Either use this param or add the SQL `LIMIT` clause in `whereEtc`; don't do both.)

**Note:** `db.findOne(.)` has the same signature as `db.find(.)`, except of course, that it doesn't have a `limit` parameter (and neither does it expect to see the `LIMIT` clause in `whereEtc`).

`ORDER BY`, `LIMIT`  Etc.
------------------------------
Everything in `whereEtc` is placed directly in the executed SQL. (Of course, placeholder-substitution is performed carefully. More on this later.) Thus, by using `whereEtc`, not only can you specify additional matching conditions (like `AND (doc->>'score')::int >= 75`), but you can also include other SQL clauses such as `ORDER BY`, `LIMIT` etc.

**SORTING:**
Continuing the above exam-results example, to find results for *Subject M* sorted by *Student IDs* (lowest to highest):
```py
db.find({"subjectId": "M"},
    whereEtc="ORDER BY doc->>'studentId' ASC"
)
```
The underlying SQL executed by PogoDB will be:
```sql
SELECT doc FROM pogotbl WHERE doc @> '{"subjectId": "M"}'
    ORDER BY doc->>'studentId' ASC;
```

**LIMITING:**
To find the *top 2* results for *Subject M*, we can use:
```py
db.find({"subjectId": "M"},
    whereEtc="ORDER BY (doc->>'score')::int DESC",
    limit=2
)
```
Or equivalently:
```py
db.find({"subjectId": "M"},
    whereEtc="ORDER BY (doc->>'score')::int DESC LIMIT 2"
)
```
In either case, the underlying SQL executed by PogoDB will be:
```sql
SELECT doc FROM pogotbl WHERE doc @> '{"subjectId": "M"}'
    ORDER BY (doc->>'score')::int DESC
    LIMIT 2;
```

**PLACEHOLDERS:**
Let's write a function for finding the top N (`n`) results for a given subject (`subjectId`), at or above a given threshold (`minScore`).
```py
import pogodb;
dbConnect = pogodb.makeConnector("postgres://..dsn..");

@dbConnect
def getTopN (n, subjectId, minScore, db):
  return db.find({"subjectId": subjectId},
    whereEtc="AND (doc->>'score')::int >= %s ORDER BY (doc->>'score')::int DESC",
    argsEtc=[minScore],
    limit=n
  );
```
Alternatively:
```py
@dbConnect
def getTopN (n, subjectId, minScore, db):
  return db.find({"subjectId": subjectId},
    whereEtc="AND (doc->>'score')::int >= %s ORDER BY (doc->>'score')::int DESC LIMIT %s",
    argsEtc=[minScore, n],
  );
```
Note: Placeholder substitution is deferred to [Psycopg's `cursor.execute(.)` method](https://www.psycopg.org/docs/cursor.html#cursor.execute), which should prevent [SQL-injection](https://owasp.org/www-community/attacks/SQL_Injection).

**Warning:** Do **NOT** use string concatenation (i.e. `+`, `str.join(.)`, etc.) or string interpolation (i.e. `%`, `str.format(.)`,  etc.) along with `whereEtc`. Pass `argsEtc` instead.


Executing Raw SQL
------------------------
If you'd like to execute raw SQL, we recommend using [Psycopg](https://www.psycopg.org/) directly. We recommend *against* using `db._execute(.)`.

Typically, `db._execute(.)` should only be relevant to PogoDB's maintainers. It accepts three parameters:
1. `stmt` (required): The SQL statement to be executed.
2. `args` (optional): Tuple (or list) for `%s` placeholder substitution.
3. `fetch` (optional): Either `None` (optional), `"one"` or `"all"`.

Parameters `stmt` and `args` are passed directly to Psycopg's `cursor.execute(.)` method. Based on `fetch`, none, one or all records are fetched.

A close cousin to `db._execute(.)` is `db._findSql(.)`, which is useful for executing `SELECT` queries. It only accepts `stmt` (required) and `args` (optional), as described above. It fetches all matching results, plucks the `doc` column, ensures dot-accessibility of dictionary objects, and returns the result.

Licensing
------------
Copyright (c) 2020 Polydojo, Inc.

**Software Licensing:**  
The software is released "AS IS" under the **Apache License 2.0**, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED. Kindly see [LICENSE.txt](https://github.com/polydojo/pogodb/blob/master/LICENSE.txt) for more details.

**No Trademark Rights:**  
The above software licensing terms **do not** grant any right in the trademarks, service marks, brand names or logos of Polydojo, Inc.
