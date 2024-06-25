#!/usr/bin/env python
import datetime
import gzip
import re

import pandas as pd

# docker logs trunk-recorder 2> tr.log
# ansi2txt < tr.log > tr.log.log
# gzip tr.log


def parselog():
    logfile = gzip.open("tr.log.gz", "rt")
    calldict = {}
    # Define the regex pattern for our log entries
    # line = "[2024-05-09 12:31:45.009426] (info)   [pwcp25]	126C	TG:       1007 (            PWPD West 1)	Freq: 851.962500 MHz	Concluding Recorded Call - Last Update: 4s	Recorder last write:4.72949	Call Elapsed: 12"
    # log_pattern = r".*\[(\S+\s\S+)\]\s+\((\S+)\)\s+\[(\S+)\]\s+(\d+).*TG:.*\((.*)\).*Freq:\s+(\d+\.\d+).*MHz\s+(.*)"
    log_pattern = r".*\[(\S+\s\S+)\]\s+\((\S+)\)\s+\[(\S+)\]\s+(\d+)\S+\s+\S+\s+(\d+).*Freq:\s+(\d+\.\d+).*MHz\s+(.*)"
    # If you DO NOT have "talkgroupDisplayFormat": "id_tag" set, you can change the log_pattern to this below to grab the numeric
    # talkgroup numbers:
    # log_pattern = r".*\[(\S+\s\S+)\]\s+\((\S+)\)\s+\[(\S+)\]\s+(\d+)\S+\s+\S+\s+(\d+).*Freq:\s+(\d+\.\d+).*MHz\s+(.*)"
    # And if you are using "talkgroupDisplayFormat": "tag_id", try this pattern:
    # log_pattern = r".*\[(\S+\s\S+)\]\s+\((\S+)\)\s+\[(\S+)\]\s+(\d+).*(\d+).*Freq:\s+(\d+\.\d+).*MHz\s+(.*)"
    for line in logfile:
        # line = "2024-05-09T12:23:26.007469771Z [2024-05-09 12:23:26.005761] (info)   [pwcp25]	16C	TG:       2003 (                PWFD 5B)	Freq: 851.725000 MHz	Concluding Recorded Call - Last Update: 4s	Recorder last write:4.79871	Call Elapsed: 13"
        if match := re.match(log_pattern, line):
            calldata = match[7]
            # Technically this isn't a real unixtimestamp as it's not timezone aware,
            # but we're just using it to create a unique index identifier.
            calldate = datetime.datetime.strptime(match[1], "%Y-%m-%d %H:%M:%S.%f")
            callts = calldate.timestamp()
            # Index for the dict is timestamp(ish)-talkgroup
            callindex = f"{int(callts)}{int(match[5].strip())}"

            # Second round of regexp.  Now we are going to harvest data from calldata - the "everything else"
            regexp_dict = {
                "excluded": r".*(Not recording talkgroup.).*",
                "encrypted": r".*(Not Recording: ENCRYPTED).*",
                "unknown_tg": r".*(TG not in Talkgroup File).*",
                "no_source": r".*(no source covering Freq).*",
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
                            "calldate": str(calldate),
                            "loglevel": str(match[2]),
                            "system": str(match[3]),
                            "callnumber": int(match[4]),
                            "talkgroup": int(match[5].strip()),
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

    # We're going to use ChanList.csv if we have it to convert decimal talkgroups to their
    # Alpha Longform.  While this could be in the original log line, we do it here to take care
    # of logs which might not have that enabled AND it allows us to see the number value of "unlisted" tg.
    try:
        chanlist = pd.read_csv("ChanList.csv")
        calldf = pd.merge(
            left=calldf,
            right=chanlist,
            left_on="talkgroup",
            right_on="Decimal",
            how="left",
        )
        # Talkgroup was an int for matching; now it becomes a string
        calldf[["talkgroup"]] = calldf[["talkgroup"]].astype("str")
        # And now we merge in the Alpha Tag to talkgroups defined.  Undefined keep their
        # numeric value
        calldf.loc[calldf["Alpha Tag"].notna(), "talkgroup"] = calldf["Alpha Tag"]
    except Exception:
        print("We couldn't open ChanList so talkgroups will remain numeric.")
    # Finally, either way let's sort the columns in the dataframe and dump the extra columns
    # from the ChanList merge
    calldf = calldf.filter(
        [
            "calldate",
            "loglevel",
            "system",
            "callnumber",
            "callclass",
            "talkgroup",
            "frequency",
            "duration",
        ],
        axis=1,
    )
    calldf.sort_values(by="calldate", inplace=True)
    return calldf


def main():
    calldict = parselog()
    calldf = pandasconvert(calldict)
    print(calldf.head())
    calldf.to_csv("tr.csv.gz", index=False)


if __name__ == "__main__":
    main()
