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
    # Define the regex pattern for our log entries
    # line = "[2024-05-09 12:31:45.009426] (info)   [pwcp25]	126C	TG:       1007 (            PWPD West 1)	Freq: 851.962500 MHz	Concluding Recorded Call - Last Update: 4s	Recorder last write:4.72949	Call Elapsed: 12"
    # log_pattern = r".*\[(\S+\s\S+)\]\s+\((\S+)\)\s+\[(\S+)\]\s+(\d+).*TG:.*\((.*)\).*Freq:\s+(\d+\.\d+).*MHz\s+(.*)"
    log_pattern = r".*\[(\S+\s\S+)\]\s+\((\S+)\)\s+\[(\S+)\]\s+(\d+)\S+\s+\S+\s+(\d+).*Freq:\s+(\d+\.\d+).*MHz\s+(.*)"
    # If you DO NOT have "talkgroupDisplayFormat": "id_tag" set, you can change the log_pattern to this below to grab the numeric
    # talkgroup numbers:
    # log_pattern = r".*\[(\S+\s\S+)\]\s+\((\S+)\)\s+\[(\S+)\]\s+(\d+)\S+\s+\S+\s+(\d+).*Freq:\s+(\d+\.\d+).*MHz\s+(.*)"
    for line in logfile:
        if match := re.match(log_pattern, line):
            calldata = match[7]
            # Technically this isn't a real unixtimestamp as it's not timezone aware,
            # but we're just using it to create a unique index identifier.
            calldate = datetime.datetime.strptime(match[1], "%Y-%m-%d %H:%M:%S.%f")
            callts = calldate.timestamp()
            # Index for the dict is timestamp(ish)-talkgroup
            callindex = f"{int(callts)}"

            # Second round of regexp.  Now we are going to harvest data from calldata - the "everything else"
            regexp_dict = {
                "excluded": r".*(Not recording talkgroup.).*",
                "encrypted": r".*(ENCRYPTED).*",
                "unknown_tg": r".*(TG not in Talkgroup File).*",
                "standard": r".*Call Elapsed:\s+(\d+)",
            }
            for callclass, data_pattern in regexp_dict.items():
                if datamatch := re.match(data_pattern, calldata):
                    calldict[callindex] = {"callclass": callclass}
                    if callclass == "standard":
                        calldict[callindex] = {"duration": int(datamatch[1])}
                        # This log event happens at the end of a call, so we should adjust the calltime
                        # back by duration seconds to get to the start.
                        calldate = calldate + datetime.timedelta(
                            seconds=-int(datamatch[1])
                        )
                    calldict[callindex].update(
                        {
                            "calldate": calldate,
                            "loglevel": match[2],
                            "system": match[3],
                            "callnumber": int(match[4]),
                            "talkgroup": match[5].strip(),
                            "frequency": float(match[6]),
                        }
                    )
    logfile.close()
    return calldict


def pandasconvert(calldict):
    calldf = pd.DataFrame.from_dict(calldict, orient="index")
    # Technically this shouldn't be needed.  The dict construction _should_ set the class
    # but for some reason it skips setting standard.  It does set duration though so that part of
    # of the loop works.  This workaround sets the class to standard if there is a duration.
    calldf.loc[calldf["duration"].notna(), "callclass"] = "standard"
    return calldf


def main():
    calldict = parselog()
    calldf = pandasconvert(calldict)
    calldf.sort_values(by="calldate", inplace=True)
    print(calldf.head())
    calldf.to_csv("tr.csv.gz", index=False)


if __name__ == "__main__":
    main()
