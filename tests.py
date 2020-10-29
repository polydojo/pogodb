import json;
import pprint;

import pogodb;
import dotsi;

pgUrl = json.load(open("tests.py.env.json"))["DATABASE_URL"];
dbful = pogodb.makeConnector(pgUrl);

# Test shellConnect:
def test_shellConect ():
    db = pogodb.shellConnect(pgUrl);
    assert db._ranSetup is True;
    db.close();
    db.reopen();
    assert db._ranSetup is False;
    db.close();
    db.reopen();
    assert db._ranSetup is False;

# Test context manager:
def test_contextManager ():
    with pogodb.connect(pgUrl) as db:
        assert db._ranSetup is True;
    with pogodb.connect(pgUrl, skipSetup=True) as db:
        assert db._ranSetup is False;

# ----------------------------------------------------------
# Hereon, use only the decorator (@dbful) format. ----------
# ----------------------------------------------------------


# Test decorator's auto-subsequent-skipping:
@dbful
def test_autoSkiping_a (db):
    assert db._ranSetup is True;    # 1st not skipped.
@dbful
def test_autoSkiping_b (db):
    assert db._ranSetup is False;   # Subsequent skipped.
@dbful
def test_autoSkiping_c (db):
    assert db._ranSetup is False;   # Subsequent skipped.
    
# Clear table:
@dbful
def test_clearing (db):
    # Try .dropTable():
    try: db.dropTable();        # Implicit `sure=False`.
    except ValueError: assert True;
    else: assert False;
    #
    # Try .clearTable();
    try: db.clearTable();       # Implicit `sure=False`.
    except ValueError: assert True;
    else: assert False;
    #
    # Drop, ensure, assert empty, re-ensure.
    db.dropTable(sure=True);    # Expliit `sure=True`.
    db.ensureTable();
    assert db.find({}) == [];
    db.ensureTable();
    #
    # Clear, assert empty:
    db.clearTable(sure=True);   # Expliit `sure=True`.
    assert db.find({}) == [];

############################################################
# Blogging Example:
############################################################

# Sample data: :::::::::::::::::::::::::::::::::::::::::::::
userList = dotsi.fy([
    {"_id": "00", "type":"user", "name": "Alice"},
    {"_id": "01", "type":"user", "name": "Becci"},
    {"_id": "02", "type":"user", "name": "Cathy"},
]);
postList = dotsi.fy([
    {"_id": "03", "type":"post", "authorId": "00",
        "title": "Title X .. ", "body": "Body X .."},
    {"_id": "04", "type":"post", "authorId": "01",
        "title": "Title Y .. ", "body": "Body Y .."},
    {"_id": "05", "type":"post", "authorId": "02",
        "title": "Title Z .. ", "body": "Body Z .."},
    {"_id": "06", "type":"post", "authorId": "00",
        "title": "Title A .. ", "body": "Body A .."},
]);
commentList = dotsi.fy([
    {"_id": "07", "type":"comment", "authorId": "02",
        "postId": "03", "text": "Comment P .."},
    {"_id": "08", "type":"comment", "authorId": "01",
        "postId": "04", "text": "Comment Q .."},
    {"_id": "09", "type":"comment", "authorId": "00",
        "postId": "05", "text": "Comment R .."},
]);
# Helper: `sorted` wrapper for  sorting documents by `._id`.
sortid = lambda dl: sorted(dl, key=lambda d: d._id);

# Insert data: :::::::::::::::::::::::::::::::::::::::::::::
@dbful
def test_inserting__blogging_example (db):
    # Insert users:
    db.insertOne(userList[0]);
    assert db.findOne({})._id == "00";
    db.insertMany(userList[1:]);
    assert len(db.find({})) == len(userList);
    #
    # Insert posts:
    db.insertMany(postList);
    assert db.findOne("03")._id == "03";
    assert len(db.find({})) == len(userList + postList);
    #
    # Insert comments:
    db.insertMany(commentList);
    assert db.findOne("09")._id == "09";
    assert len(db.find({})) == len(userList + postList + commentList);
    #pprint.pprint(db.find({}));

# Finding data: ::::::::::::::::::::::::::::::::::::::::::::
@dbful
def test_finding__blogging_example (db):
    # .findOne():
    assert db.findOne("00") == userList[0];
    assert db.findOne("_idNotFound") is None;
    assert db.findOne({"name": "Alice"}) == userList[0];
    assert db.findOne({"name": "NameNotFound"}) is None;
    # .find():
    assert sortid(db.find({"type": "user"})) == userList;
    alicePosts = db.find({"type": "post", "authorId": "00"});
    assert sortid(alicePosts) == [postList[0], postList[-1]]
    assert sortid(db.find({})) == userList + postList + commentList;
    # TODO: .findSql(), or .find(.., whereEtc, argsEtc)

# Deleting data: :::::::::::::::::::::::::::::::::::::::::::
@dbful 
def test_deleting__blogging_example (db):
    for comment in commentList:
        db.deleteOne(comment._id);
        #r = db.find(comment._id); print("r = ", r);
        assert db.findOne(comment._id) is None;
    assert sortid(db.find({})) == userList + postList;



############################################################
# Run All Tests: ###########################################
############################################################


if __name__ == "__main__":
    for (name, val) in dict(**locals()).items():
        if name.startswith("test_") and callable(val):
            print("\nRunning %s() ..." % name)
            val();
            print("Passed.")
    print("\nGreat! All tests passed.\n");
else:
    getdb = lambda: pogodb.shellConnect(pgUrl);

# End ######################################################
