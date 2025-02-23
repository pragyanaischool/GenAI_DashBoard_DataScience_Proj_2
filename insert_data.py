# import packages
import os
import pandas as pd
import string
import re
import mysql.connector as mysql
from mysql.connector import Error

# database class for inserting the data
class database:
    def __init__(self, dbName: str, df: pd.DataFrame, table_name: str):
        self.dbName = dbName
        self.df = df
        self.table_name = table_name

    def DBConnect(self):
        conn = mysql.connect(host='localhost', user='root', password='pass@1221',
                            database=self.dbName, buffered=True)
        cur = conn.cursor()
        return conn, cur

    def emojiDB(self) -> None:
        conn, cur = self.DBConnect()
        dbQuery = f"ALTER DATABASE {self.dbName} CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci;"
        cur.execute(dbQuery)
        conn.commit()

    def createDB(self) -> None:
        conn, cur = self.DBConnect()
        cur.execute(f"CREATE DATABASE IF NOT EXISTS {self.dbName};")
        conn.commit()
        cur.close()

    def createTables(self) -> None:
        conn, cur = self.DBConnect()
        sqlFile = 'sql_schema.sql'
        fd = open(sqlFile, 'r')
        readSqlFile = fd.read()
        fd.close()

        sqlCommands = readSqlFile.split(';')

        for command in sqlCommands:
            try:
                res = cur.execute(command)
            except Exception as ex:
                print("Command skipped: ", command)
                print(ex)
        conn.commit()
        cur.close()

        return

    def preprocess_df(self, df) -> pd.DataFrame:

        df.rename({'original_text':'clean_text'}, axis=1, inplace=True) # rename 'original_text' with 'clean_text'
        df = df.drop(columns=['possibly_sensitive'], axis=1)
        # Remove hyperlinks
        rgx = lambda x: re.sub('http[s]?', '', x)
        df['clean_text'] = df['clean_text'].map(rgx)

        # Remove punctuation
        df['clean_text']= \
        df['clean_text'].apply(lambda x: x.translate(str.maketrans(' ', ' ', string.punctuation)))

        df['polarity'] = pd.to_numeric(df['polarity'],errors='coerce')  # change polarity to numeric
        df = df.dropna() # remove rows and columns with Null/NaN values.
        return df


    def insert_to_tweet_table(self) -> None:
            
        conn, cur = self.DBConnect()

        self.df = self.preprocess_df(self.df)
        
        for _, row in self.df.iterrows():
            sqlQuery = f"""INSERT INTO {self.table_name} (created_at, source, clean_text, polarity, subjectivity,
        lang, favorite_count, retweet_count, original_author, followers_count, friends_count, hashtags, user_mentions, place)
            VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);"""
            data = (row[0], row[1], row[2], row[3], (row[4]), (row[5]), row[6], row[7], row[8], row[9], row[10], row[11],
                    row[12], row[13])

            try:
                # Execute the SQL command
                cur.execute(sqlQuery, data)
                # Commit your changes in the database
                conn.commit()
                print("Data Inserted Successfully")
            except Exception as e:
                conn.rollback()
                print("Error: ", e)
        return

    def db_execute_fetch(self, *args, many=False, tablename='', rdf=True, **kwargs) -> pd.DataFrame:
        connection, cursor1 = self.DBConnect(**kwargs)
        if many:
            cursor1.executemany(*args)
        else:
            cursor1.execute(*args)

        # get column names
        field_names = [i[0] for i in cursor1.description]

        # get column values
        res = cursor1.fetchall()

        # get row count and show info
        nrow = cursor1.rowcount
        if tablename:
            print(f"{nrow} recrods fetched from {tablename} table")

        cursor1.close()
        connection.close()

        # return result
        if rdf:
            return pd.DataFrame(res, columns=field_names)
        else:
            return res


if __name__ == "__main__":
    df = pd.read_csv('processed_tweet_data.csv')
    db = database(dbName='Tweetdb', df=df, table_name='Tweet')
    db.createDB()
    db.emojiDB()
    db.createTables()
    db.insert_to_tweet_table()
    
