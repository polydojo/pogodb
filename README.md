PogoDB
=======

Simple NoSQL wrapper for Postgres' JSONB type. 

Installation
--------------
PogoDB is installable via pip, following a two-step process:
1. `pip install pogodb`
2. `pip install psycopg2` ***OR*** `pip install psycopg2-binary`

Since the `psycopg2`/`psycopg2-binary` split, instead of us forcing a dependency on either one, it makes more sense for you to install your preferred package. PogoDB should work with either. *Tip:*  If `pip install psycopg2` fails, try `pip install psycopg2-binary`.

Quick Start:
---------------
To connect from a Python Shell, use `pogodb.shellConnect()`.
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

Connecting Properly:
--------------------------

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
The decorator supplies the `db` parameter to the decorated function. The parameter is supplied by name, so it must be called `db`, not `myDb` or something else.


Inserting Data:
--------------------------
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

Retrieving Data:
--------------------
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
# Output: Alice - AA
```
*Note:* If no matching document is found, `.findOne(.)` returns `None` while `.find(.)` returns an empty list.

Updating Data:
-------------------
In continuation with the above code snippet ...
```py
# Replace document:
taskA.text = "New AA"           # <-- Update in-memory
taskA.x = {"y": 10, "z": 20}
db.replaceOne(taskA);           # <-- Propagate to db
print([db.findOne(taskA._id).text, taskA.x])
# Output: ['New AA', {'y': 10, 'z': 20}]

# Increment within document:
db.incr({"_id": "a"}, ["x", "y"], 1) # Incr x.y by 1
print(db.findOne("a").x)
# Output: {'y': 11, 'z': 20}

# Decrement:
db.decr({"_id": "a"}, ["x", "z"], 1) # Decr x.z by 1
print(db.findOne("a").x)
# Output: {'y': 11, 'z': 19}
```

Deleting Data:
------------------
In continuation with the above code snippet ...
```py
# Delete by _id:
db.deleteOne("a");
print(db.findOne("a"))
# Output: None
```
As of writing, you can only delete one document at a time, by `_id`.

Under The Hood
---------------------
Under the hood, PogoDB creates a single table named `pogo_tbl` with a single `JSONB` column named `doc` (for document).

**TODO:** Write documentation regarding lower-level functions such as `db.findSql(.)` and `db.execute(.)`.

Type Identifiers
-------------------

PogoDB doesn't include buckets, collections or other such concepts for **logically grouping** different types of documents. But you can *(and should)* use a key for differentiating objects of various types.

**Convention:**  
Keeping things simple, we recommend using the `"type"` key for indicating the type of the object.

**Example:**  
In a blogging app, you'll have to deal with users, posts, comments and other types of objects. 

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

Licensing
-----------
Copyright (c) 2020 Polydojo, Inc.

The software is released "AS IS" under the **Apache License 2.0**, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED. Kindly see [LICENSE.txt](https://github.com/polydojo/pogodb/blob/master/LICENSE.txt) for more details.
