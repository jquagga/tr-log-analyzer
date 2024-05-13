# tr-log-analyzer

[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/jquagga/tr-log-analyzer/main?labpath=trlog.ipynb)
[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/jquagga/tr-log-analyzer/badge)](https://securityscorecards.dev/viewer/?uri=github.com/jquagga/tr-log-analyzer)

A python notebook to parse [trunk-recorder](https://github.com/robotastic/trunk-recorder)'s log file to generate stats.

## Usage

So there are two ways to go here. If you just want to run the script and get a .csv output of all of the calls and what type they are etc, the `trlog.py` is the way to go.

The cooler way in my opinion is to open up the Juypter notebook. That'll take the log file, parse it all with regexp and then display graphs with statistics and other cool stuff.

### Recommended / easy route

The simplest way is to configure trunk-recorder to save logs to the log dir. If you're using docker, make sure you have your timezone in the docker set correct (just take a quick look at the log files and make sure the times seem correct). Otherwise you'll still get the data, it's just the time will be off.

trunk-recorder saves the log file daily. Copy that over, rename it to tr.log and gzip it.
Also copy over your Chanlist.csv so you have your mapping of talk group numbers to talk group Alpha Tags.

Put those in a directory, run jupyter-lab and run the notebook. Ta-dah! If that later part is difficult where you're at, [![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/jquagga/tr-log-analyzer/main?labpath=trlog.ipynb) will spin up a little VM running Juypter (give it a minute after following the link to do all of the setup). You can click the folder icon on the right side and then upload your gzip'ed log and your Chanlist.csv

## todo

There's time series stuff I'd like to add and figuring out other plotly graphs. But here is a start.
