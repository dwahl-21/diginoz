import sqlite3 as sql
import toml
import re
import os
import hashlib

DATAROOT = os.path.abspath(os.path.expanduser("~/diginoz/root"))

def getIndex(root: str) -> dict:
    '''
    Builds an index of a folder structure recursively and returns a list of objects containing hashes and metadata of files.
    
    Parameters:
        root (str): path to the root directory
    
    Returns:
        index (list): list containing dicts with path and file-content hashes and metadata dict
    '''
    index: list = []
    buildIndex(root, index)
    return index

def buildIndex(root: str, index: list) -> None:
    '''
    Recursively iterate over all files in the given path including subdirectories.
    
    Parameters:
        root (str): path to the directory to list all files of
        index (list): list to append the found information to
    '''
    for f in os.listdir(root):
        f1_path: str = os.path.join(root, f)
        if os.path.isdir(f1_path):
            buildIndex(f1_path, index)
        else:
            with open(f1_path, "rb") as fp:
                bContent: bytes = fp.read()
                metaDataRE: re.Match = re.match("<!--([\S\s]*)-->[\S\s]*", bContent.decode("utf-8"), re.MULTILINE)
                metaDataTOML: dict = toml.loads(metaDataRE.groups()[0].strip() if metaDataRE else "")
                metaData = metaDataTOML["metadata"] if ("metadata" in metaDataTOML.keys()) else {}
                index.append({"pathHash": hashlib.sha256(f1_path.encode('utf-8'), usedforsecurity=False).hexdigest(),"path": f1_path, "fileHash": hashlib.sha256(bContent, usedforsecurity=False).hexdigest(), "metaData": metaData})
                # print({f"{hashlib.sha256(f1_path.encode('utf-8')).hexdigest()}": hashDigest, "metadata": metaData})

def getFileHashForFile(cursor: sql.Cursor, pathHash: str) -> str:
    '''
    Returns the fileHash currently saved in the database for a given file (pathHash).
    
    Parameters:
        cursor (sql.Cursor): cursor for the current database connection
        pathHash (str): SHA256 hexdigest of the path to the file
    
    Returns:
        result (str): fileHash in database or empty string if file is not in database
    '''
    result: str = cursor.execute(f"SELECT fileHash FROM files WHERE pathHash='{pathHash}' LIMIT 1;").fetchone()
    return result[0] if result else ""

def updateHashes(conn: sql.Connection, fileDict: dict) -> None:
    '''
    updates the data in the database and adds new files

    Parameters:
        conn (sql.Connection): connection to the database
        fileDict (dict[str]): dictionary containing all info about the file (path,pathHash,fileHash,tags)
    '''
    cursor = conn.cursor()
    dbHash: str = getFileHashForFile(cursor, fileDict["pathHash"])
    tags: str = ";".join([x.strip() for x in fileDict["metaData"]["tags"]])
    if dbHash == "":
        cursor.execute(f"INSERT INTO files (pathHash, path, fileHash, tags) VALUES ('{fileDict['pathHash']}','{fileDict['path']}','{fileDict['fileHash']}','{tags}');")
    elif dbHash != fileDict["fileHash"]:
        cursor.execute(f"UPDATE files SET fileHash='{fileDict['fileHash']}', tags='{tags}' WHERE pathHash='{fileDict['pathHash']}';")
    conn.commit()
    cursor.close()

def getFiles(conn: sql.Connection) -> None:
    '''
    Lists all entries contained in the database

    Parameters:
        conn (sql.Connection): connection to the database
    '''
    cursor: sql.Cursor = conn.cursor()
    result: list = cursor.execute("SELECT * FROM files;").fetchall()
    for file in result:
        print(file)
    cursor.close()

def removeOldHashes(conn: sql.Connection) -> None:
    '''
    Cleans the database from entries for files which do no longer exist

    Parameters:
        conn (sql.Connection): connection to the database
    '''
    cursor: sql.Cursor = conn.cursor()
    entries: tuple[dict] = cursor.execute("SELECT path,pathHash FROM files;").fetchall()
    for entry in entries:
        if not os.path.isfile(entry[0]):
            cursor.execute(f"DELETE FROM files WHERE pathHash='{entry[1]}';")
    cursor.close()
    conn.commit()

def searchTag(conn: sql.Connection, tag: str) -> tuple[dict]|None:
    '''
    Returns a list of files with have been tagged with the tag in question.

    Parameters:
        conn (sql.Connection): connection to the database
        tag (str): the tag to search for

    Returns:
        result (tuple): a list of entries which match the tag
    '''
    cursor: sql.Cursor = conn.cursor()
    result: tuple[dict]|None = cursor.execute(f"SELECT pathHash,path,tags FROM files WHERE tags LIKE '%{tag}%';").fetchall()
    cursor.close()
    return result

if __name__ == "__main__":
    with sql.connect("diginoz.db") as conn:
        cursor: sql.Cursor = conn.cursor()

        # input from the user, either a tag or 'QUIT'
        option: str = ""
        while option != "QUIT":
            os.system("cls")
            # list all currently tracked files in the database
            # getFiles(conn)
            # print("-"*64)

            # remove old hashes before updating and inserting new ones
            # to circumvent moving files and having duplicate entries
            removeOldHashes(conn)

            # build index for data root
            index: list = getIndex(DATAROOT)
            for file in index:
                updateHashes(conn, file)

            # search for a specific tag and print out the result
            results: tuple[dict] = searchTag(conn, option.lower())

            for result in results:
                path: str = result[1].replace("\\","/")
                print(f"file://{path} <{result[2]}>")
                print("")
            option = input("Tag to search for (QUIT to exit program): ")
        cursor.close()
