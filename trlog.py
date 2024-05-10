#!/usr/bin/env python
import datetime
import gzip
import re

import pandas as pd

# docker logs trunk-recorder 2> tr.log
# ansi2txt < tr.log > tr.log.log
# gzip tr.log


def parselog():
    calldict = {}
    logfile = gzip.open("tr.log.gz", "rt")
    for line in logfile:
        # Define the regex pattern for our log entries
        log_pattern = r".*\[(\S+\s\S+)\]\s+\((\S+)\)\s+\[(\S+)\]\s+(\d+)\S+\s+\S+\s+(\d+).*Freq:\s+(\d+\.\d+).*MHz\s+(.*)"
        # Example log entry
        # line = "[2024-05-09 12:31:45.009426] (info)   [pwcp25]	126C	TG:       1007 (            PWPD West 1)	Freq: 851.962500 MHz	Concluding Recorded Call - Last Update: 4s	Recorder last write:4.72949	Call Elapsed: 12"
        match = re.match(log_pattern, line)
        # Ok, we have a first stage match.  This gets the date, loglevel, system, callnumber, talkgroup, frequency and
        # everything else to parse. Then we will regex again to pull data from everything else.
        if match:
            calldata = match[7]
            # Technically this isn't a real unixtimestamp as it's not timezone aware,
            # but we're just using it to create a unique index identifier.
            calldate = datetime.datetime.strptime(match[1], "%Y-%m-%d %H:%M:%S.%f")
            callts = calldate.timestamp()
            # Index for the dict is timestamp(ish)-talkgroup
            callindex = str(int(callts)) + "-" + match[5]

            # Second round of regexp.  Now we are going to harvest data from calldata - the "everything else"
            # Yes, this does need to be refactored as a loop ...
            # Note to me, make the regexp a list, for loop it, and change continue to break
            # Not recording talkgroup. Priority is -1.
            data_pattern = r".*(Not recording talkgroup.).*"
            datamatch = re.match(data_pattern, calldata)
            if datamatch:
                calldict[callindex] = {"excluded": True}
                calldict[callindex].update(
                    {
                        "calldate": calldate,
                        "loglevel": match[2],
                        "system": match[3],
                        "callnumber": match[4],
                        "talkgroup": match[5],
                        "frequency": match[6],
                    }
                )
                continue
            # Not Recording: ENCRYPTED - src: 3290217
            data_pattern = r".*(ENCRYPTED).*"
            datamatch = re.match(data_pattern, calldata)
            if datamatch:
                calldict[callindex] = {"encrypted": True}
                calldict[callindex].update(
                    {
                        "calldate": calldate,
                        "loglevel": match[2],
                        "system": match[3],
                        "callnumber": match[4],
                        "talkgroup": match[5],
                        "frequency": match[6],
                    }
                )
                continue
            # Not Recording: TG not in Talkgroup File
            data_pattern = r".*(TG not in Talkgroup File).*"
            datamatch = re.match(data_pattern, calldata)
            if datamatch:
                calldict[callindex] = {"unknown_talkgroup": True}
                calldict[callindex].update(
                    {
                        "calldate": calldate,
                        "loglevel": match[2],
                        "system": match[3],
                        "callnumber": match[4],
                        "talkgroup": match[5],
                        "frequency": match[6],
                    }
                )
                continue
            # Concluding Recorded Call - Last Update: 4s	Recorder last write:4.4819	Call Elapsed: 7
            data_pattern = r".*Call Elapsed:\s+(\d+)"
            datamatch = re.match(data_pattern, calldata)
            if datamatch:
                calldict[callindex] = {"duration": datamatch[1]}
                calldict[callindex].update(
                    {
                        "calldate": calldate,
                        "loglevel": match[2],
                        "system": match[3],
                        "callnumber": match[4],
                        "talkgroup": match[5],
                        "frequency": match[6],
                    }
                )
                continue
    logfile.close()
    return calldict


def pandasconvert(calldict):
    return pd.DataFrame.from_dict(calldict, orient="index")


def main():
    calldict = parselog()
    calldf = pandasconvert(calldict)
    print(calldf)
    calldf.to_csv("tr.csv.gz", index=False)


if __name__ == "__main__":
    main()
