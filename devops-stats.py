import argparse
import os
import sys
import pandas as pd
import numpy as np
import subprocess as subprocess
import time
import fileinput
import multiprocessing

from itertools import cycle
from datetime import datetime
from matplotlib import markers

import matplotlib.dates as dates
import matplotlib.pyplot as plt

MODE_PROJECT = "project"
MODE_GENERAL = "gen"
MODE_FOLDER  = "folder"

METRIC_MODE_COMMIT  = "commit"
METRIC_MODE_RELEASE = "release"

UPDATES_DATES_FILE              = "update-dates.csv"
UPDATES_DATES_FILE_LOCK         = multiprocessing.Lock()
UPDATES_DATES_COMMIT_TABLE      = dict()
UPDATES_DATES_COMMIT_TABLE_LOCK = multiprocessing.Lock()

DEFAULT_START_DATE = "2015,1,1"

FONT_SIZE_LABEL     = 12
FONT_SIZE_LEGEND    = 10

SANDBOX_DIR=""

def plot(mode, metric_mode, repo_dir, start_date):

    # check if we're handling 'releases' or 'commits', use the appropriate
    # wording from now on (e.g. in graph titles, print statements, etc.)
    if (metric_mode == METRIC_MODE_COMMIT):
        _metric_str = "commits"
    else:
        _metric_str = "releases"

    # sanity check keeps track of total nr. of releases/commits (can be used 
    # to quickly compare w/ numbers on github)
    release_num = 0

    # parse the start date, pass it to a datetime object
    _start_date = start_date.split(",")
    _start_date = datetime(int(_start_date[0]), int(_start_date[1]), int(_start_date[2]))

    # read contents of .csv file into a data frame
    _updt_list_raw = pd.read_csv(UPDATES_DATES_FILE, sep=",")
    
    # OBJECTIVES:
    #   a) plot a line for each different 'app-name'
    #   b) if MODE_PROJECT is set, plot the totals on a second subplot

    # 1.1) let's get the plottin' started...
    _fig = plt.figure()

    # 1.2) colors & line styles
    color_cycler = cycle(['b', 'g', 'r', 'c', 'm', 'y', 'k', 'gray'])
#    linestyle_cycler = cycle(['-', '--', ':', '-.'])
    linestyle_cycler = cycle([''])
    markerstyle_cycler = cycle(['o', 'v', '^', '<', '>', '8', 's', 'h', 'D', '+', 'x', '*'])

    # 1.3) add subplots
    
    # 1.3.1) if MODE_PROJECT, we're plotting more than one subplot
    if (mode == MODE_PROJECT):
        _updt_plot = _fig.add_subplot(211)
    else:
        _updt_plot = _fig.add_subplot(111)

    # 2.1) get the unique 'app-name' 
    _app_names = pd.unique(_updt_list_raw['app-name'].values.ravel())
    
    print "devops-stats :: found " + str(len(_app_names)) + " unique 'app-name' values : " + _app_names

    # 2.2) build an histogram (# of updates per day) for each app name + for 
    # the total nr. of updates
    _y_max = 0
    _updt_list_hist_total = dict()

    for _app_name in _app_names:
        
        print "devops-stats :: plotting 'app-name' = " + _app_name
        
        # 2.2.1) build histogram for each app name
        _updt_list_hist_app = dict()
        
        # this complicated line filters the _updt_list_raw rows w/ the current 
        # app name
        for _index, _row in _updt_list_raw.loc[_updt_list_raw['app-name'] == _app_name].iterrows():

            if (datetime.strptime(_row[0], "%Y-%m-%d") < _start_date):
                continue

            # update the nr. of releases/commits
            release_num += 1

            # update (add or increment) a position in the histogram by 
            # date (i.e. _row[0])
            if _row[0] in _updt_list_hist_app:
                _updt_list_hist_app[_row[0]] += 1 
            else:
                _updt_list_hist_app[_row[0]] = 1

            # update the totals histogram only if MODE_PROJECT is set
            if (mode == MODE_PROJECT):

                if _row[0] in _updt_list_hist_total:
                    _updt_list_hist_total[_row[0]] += 1 
                else:
                    _updt_list_hist_total[_row[0]] = 1

        # 2.3.2) x & y arrays for plotting
        _x = []
        _y = []

        for _key in sorted(_updt_list_hist_app):
            # convert the date strings in _updt_list_hist_app to datetime objects
            _x.append(datetime.strptime(_key, "%Y-%m-%d"))
            _y.append(_updt_list_hist_app[_key])

        # 2.2.3) use plot_date() for nr. of releases vs. date (Y-m-d)
        _updt_plot.plot_date(
            dates.date2num(_x), _y,                 # actual data
            linestyle=linestyle_cycler.next(),      # line styles
            color=color_cycler.next(),              # colors
            marker=markerstyle_cycler.next(),       # marker styles
            linewidth=1.5,
            label=_app_name.rstrip())               # label is app name

        # keep track of the maximum nr. of updates per day (to set the right 
        # limits for the y axis)
        if _y_max < max(_y):
            _y_max = max(_y)

    print "devops-stats :: # of " + _metric_str + " = " + str(release_num)
        
    # 2.2.4) title
    _title = "# of " + _metric_str + " per day (" + repo_dir.split("/")[-1].rstrip() + ")"
    # if MODE_FOLDER is active, add a subtitle with the folder/file name
    if (mode == MODE_FOLDER):
        _title += "\n(folder " + repo_dir + ")"
    _updt_plot.set_title(_title)
    
    # 2.2.5) x and y axis labels
    if (mode == MODE_PROJECT):
        # HACK : hide the axis text if MODE_PROJECT is set (we'll have 2 stacked 
        # subplots, if we use 2 x axis labels, we get a crowded image)
        _fr = plt.gca()
        _fr.axes.xaxis.set_ticklabels([])
    else:
        _updt_plot.set_xlabel("date (Y/M/D)")
        # rotate x labels by 90 deg
        x_labels = _updt_plot.get_xticklabels()
        plt.setp(x_labels, rotation=45, fontsize=FONT_SIZE_LABEL)
    # set the x axis limits to [start date, today's date] 
    _updt_plot.set_xlim([
        _start_date, 
        datetime.now()])
    _updt_plot.set_ylabel("# of " + _metric_str)
    _updt_plot.set_ylim(0, _y_max + 1)
    
    _updt_plot.grid(True)

    # 2.2.6) legend
    _updt_plot.legend(
        bbox_to_anchor=(1, 1),      # outside the graph
        loc='upper left',           # this helps the legend to go outside (don't know why)
        fontsize=FONT_SIZE_LEGEND,  # font size
        numpoints=1,                # only 1 marker per legend item (default is 2)
        ncol=1)                     # single column legend

    # 2.3) plot the totals in a different subplot (if MODE_PROJECT is set)
    if (mode == MODE_PROJECT):

        # 2.3.1) 2nd subplot of a 2 row x 1 column plot
        _updt_plot_totals = _fig.add_subplot(212)

        # 2.3.2) x & y arrays for plotting
        _x = []
        _y = []

        for _key in sorted(_updt_list_hist_total):
            _x.append(datetime.strptime(_key, "%Y-%m-%d"))
            _y.append(_updt_list_hist_total[_key])        

        # 2.3.3) plot w/ plot_date()
        _updt_plot_totals.plot_date(
            dates.date2num(_x), _y,
            linestyle=linestyle_cycler.next(),
            color=color_cycler.next(),
            marker=markerstyle_cycler.next(),
            linewidth=1.5,
            label='total')

        # 2.3.4) subplot title
#        _title = "# of Releases per Day (total)"
#        _updt_plot_totals.set_title(_title)
        
        # 2.3.5) x and y axis labels
        _updt_plot_totals.set_xlabel("date (Y/M/D)")
        # rotate x labels by 90 deg
        x_labels = _updt_plot_totals.get_xticklabels()
        plt.setp(x_labels, rotation=45, fontsize=FONT_SIZE_LABEL)
        _updt_plot_totals.set_xlim([
            _start_date, 
            datetime.now()])
        _updt_plot_totals.set_ylim(0, max(_y) + 1)
        _updt_plot_totals.set_ylabel("# of " + _metric_str)

        _updt_plot_totals.grid(True)

        # 2.3.6) legend
        _updt_plot_totals.legend(
            bbox_to_anchor=(1, 1),
            loc='upper left', 
            fontsize=FONT_SIZE_LEGEND, 
            numpoints=1, 
            ncol=1)

    # 2.4) save the plot as <repo_name>.<mode>.<metric_mode>.png
    plt.savefig(SANDBOX_DIR + "/" + repo_dir.split("/")[-1] + "." + mode + "." + metric_mode + ".png", bbox_inches='tight')
    
def get_release_date((tag, repo_dir, app_name)):

    # 1) get the LATEST commit hashes related with 'tag' on 'repo_dir'. this 
    # will allows us to distinguish tags which actually introduce differences 
    # in 'repo_dir' (note that diff. tags may not introduce changes in 
    # 'repo_dir')

    # HACK: for some reason, using _tag directly 
    # as an argument to subprocess.Popen() doesn't work
    _cmd = 'git log ' + tag + ' --date=short --pretty="%ad,%H" -- ' + repo_dir + ' | sort -g | tail -1'

    try:
        _p1 = subprocess.Popen(
            [_cmd], 
            stdout = subprocess.PIPE,
            shell = True)
        _p1.wait()
        (_commit, _error) = _p1.communicate()
        
    except subprocess.CalledProcessError as e:
        sys.stderr.write(
            "devops-stats ::  ERROR: output = %s, error code = %s\n" 
            % (e.output, e.returncode))

    if (not _commit):
        return

    # _commit (the output of _p1) will have the form <date>,<commit-hash>. we 
    # now need to split it
    # why 'van_damme'? because of the 'epic *split*'! ok, i'll shut up now...
    _commit_van_damme = _commit.rstrip().split(",")
    if (len(_commit_van_damme) < 2):
        return
    _date = _commit_van_damme[0].rstrip()
    _commit_hash = _commit_van_damme[1].rstrip()

    UPDATES_DATES_COMMIT_TABLE_LOCK.acquire()   # *** commit table LOCK ***

    # if _date is empty or the LATEST commit for tag is shared with
    # a previous tag (i.e. it has been added to the commit table by a previous 
    # tag), stop here
    if (_commit_hash in UPDATES_DATES_COMMIT_TABLE):
        UPDATES_DATES_COMMIT_TABLE_LOCK.release()   # *** commit table UNLOCK ***
        print "skipped release " + tag 
        return

    # otherwise, add the commit hash to the commit table. this table allows 
    # us to determine if a given commit has already been seen as belonging to 
    # a tag for 'repo_dir'
    UPDATES_DATES_COMMIT_TABLE[_commit_hash] = 1

    UPDATES_DATES_COMMIT_TABLE_LOCK.release()   # *** commit table UNLOCK ***

    # get the exact date of the release (not the commit date)
    _cmd = 'git log -1 --date=short --pretty="%ad" ' + tag

    try:
        _p2 = subprocess.Popen(
            [_cmd], 
            stdout = subprocess.PIPE,
            shell = True)
        _p2.wait()
        (_date, _error) = _p2.communicate()
        
    except subprocess.CalledProcessError as e:
        sys.stderr.write(
            "devops-stats ::  ERROR: output = %s, error code = %s\n" 
            % (e.output, e.returncode)) 

    # write <date>,<tag> to the file (respecting the update file lock)
    UPDATES_DATES_FILE_LOCK.acquire()   # *** update file LOCK ***
    
    _output_file = open(UPDATES_DATES_FILE, 'a')
    _output_file.write("%s,%s,%s\n" % (_date.rstrip(), tag, app_name))
    _output_file.close()
    
    UPDATES_DATES_FILE_LOCK.release()   # *** update file UNLOCK ***
    
    return
    
def get_app_name(repo_dir):
    # HACK: cd into the git repo (we run git commands from there)  
    if os.path.isfile(repo_dir):
        os.chdir(os.path.dirname(repo_dir))
    else:
        os.chdir(repo_dir)

    # command to get the name of the application
    _p_cmd = 'basename $(git rev-parse --show-toplevel)'
    try:
        _p = subprocess.Popen(
            [_p_cmd], 
            stdout = subprocess.PIPE,
            shell = True)
        _p.wait()
        (_app_name, _error) = _p.communicate()  
        
    except subprocess.CalledProcessError as e:
        sys.stderr.write(
            "devops-stats ::  ERROR: output = %s, error code = %s\n" 
            % (e.output, e.returncode))    
        
    return _app_name.rstrip()

def append_tags(git_repo, metric_mode):

    # re-open the output file in 'a'ppend mode
    _output_file = open(UPDATES_DATES_FILE, 'a')

    # HACK : cd into the git repo (we run git commands from there)
    os.chdir(git_repo)
    # get the repo name
    _app_name = get_app_name(git_repo)

    # depending on which metric we're collecting (releases/commits) 
    # the git commands to run are different
    if (metric_mode == METRIC_MODE_COMMIT):
        # list ALL commits
        _p_cmd = 'git log --all --date=short --format=format:"%ad,%H,' + _app_name + '"'
        _p = subprocess.Popen(
            [_p_cmd], 
            shell = True,
            stdout=_output_file)
        # wait for _p to finish, otherwise plot() will work on an empty file
        _p.wait()

        # HACK : this seems to be necessary for some reason...
        _output_file.write("\n")

    else:
        # we want to run the command 'git tag | xargs -I@ git log 
        # --date=short --format=format:"%ad @%n" -1 @ > UPDATES_DATES_FILE)
        # we use 'subprocess' for this (and not the usual os.system())
        _p1 = subprocess.Popen(['git', 'tag'], stdout=subprocess.PIPE)
        # notice that stdin for p2 is p1, and stdout is _output_file
        # we append a line like '<date>,<version>,<app-name>' to the output file
        _p2_cmd = 'xargs -I@ git log --date=short --format=format:"%ad,@,' + _app_name + '%n" -1 @'
        _p2 = subprocess.Popen(
            [_p2_cmd], 
            shell = True,
            stdin=_p1.stdout, 
            stdout=_output_file)
        _p2.wait() 

def pre_process(mode, metric_mode, repo_dir):

    # erase the contents of the output file (if any), add a header, close it
    _output_file = open(UPDATES_DATES_FILE, 'w+')
    if (metric_mode == METRIC_MODE_COMMIT):
        _output_file.write('date,version,app-name\n')
    else:
        _output_file.write('date,commit,app-name\n')
    _output_file.flush()
    _output_file.close()

    if (mode == MODE_PROJECT):
        # re-open the output file in 'a'ppend mode
        _output_file = open(UPDATES_DATES_FILE, 'a')     

        # get a list of git repositories in the base directory (we assume each 
        # subdirectory is a git repo)
        _git_repos = [_sub_dir for _sub_dir in os.listdir(repo_dir) if os.path.isdir(os.path.join(repo_dir, _sub_dir))]

        for _git_repo in _git_repos:

            # append the list of tags to the output file
            _git_repo = repo_dir + "/" + _git_repo
            append_tags(_git_repo, _metric_mode)
        
    elif (mode == MODE_GENERAL):
        append_tags(repo_dir, _metric_mode)
        
    elif (mode == MODE_FOLDER):
        # HACK: cd into the git repo (we run git commands from there)  
        if os.path.isfile(repo_dir):
            os.chdir(os.path.dirname(repo_dir))
        else:
            os.chdir(repo_dir)

        _output_file = open(UPDATES_DATES_FILE, 'w+')
        _output_file.write('date,version,app-name\n')
        _output_file.flush()
        _output_file.close()
        
        # 1) extract all tag names in the repo
        
        _p1 = subprocess.Popen(
            ['git tag'], 
            stdout = subprocess.PIPE,
            shell = True)

        _p1.wait()
        (_tags, _error) = _p1.communicate()
        
        # 2) run 'git log <tag-num> (...)' for each tag in the list. record 
        # the date of the latest commit, and add <latest_commit_date>,<version> 
        # to the output file (this guarantees one unique entry per version)
        
        # 2.1) prepare the tag list
        
        _tag_list = []
        # adjust _tags (separate each tag line, strip the last empty line)
        _tags = _tags.rstrip().split("\n")
        # NEW: get the app name
        _app_name = get_app_name(repo_dir)
        
        for _tag in _tags:          
            _tag_list.append((_tag.rstrip(), repo_dir, _app_name))
        
        # 2.2) since 'git log tag (...)' takes a lot of time, let's increase
        # speed a bit more by running several commands in paralell. we use 
        # a thread pool for that.        
        _thread_pool = multiprocessing.Pool()        
        
        # 2.3) pass the tag list to the thread pool...
        _thread_pool.map(get_release_date, _tag_list)
        
        # ... and now, we wait (hopefully a shorter time)
        _thread_pool.close()
        _thread_pool.join()
            
    # HACK : cd back to the sandbox...
    os.chdir(SANDBOX_DIR)

if __name__ == '__main__':
    
    # use an ArgumentParser to provide a nice CLI
    parser = argparse.ArgumentParser()
    
    # options (self-explanatory)
    parser.add_argument("--repo_dir", 
                         help="dir of git repo to gather stats from. this could \
                         be the base dir of the repo, a particular folder/file in \
                         a repo (see '--folder' option), or even a base directory \
                         with multiple repos to be analyzed (see '--project' option).")
    parser.add_argument("--project", 
                         help="use this option if <repo-dir> is not \
                         an actual git repo but a base directory where multiple \
                         git repos are located. the script will generate a \
                         graph combining all individual repos.",
                         action="store_true")    
    parser.add_argument("--folder", 
                         help="set this flag to gather \
                         get stats from a particular folder or \
                         file in the repository. we assume <repo-dir> is \
                         the absolute path to this folder or file in the \
                         repo. only valid if '--project' isn't active.",
                         action="store_true")
    parser.add_argument("--release", 
                         help="look at release stats (not commits). this is the default behavior.",
                         action="store_true")
    parser.add_argument("--commit", 
                         help="look at commit stats (not releases).",
                         action="store_true")
    parser.add_argument("--out_dir", 
                         help="dir to save graphs.")
    parser.add_argument("--start_date", 
                         help="start date for release/commit history. e.g.: \
                         '--start_date 2015,2,1' for Feb 1st 2015. default is \
                         '2015,1,1'")

    args = parser.parse_args()
    
    # some arg processing here

    if (args.commit):
        _metric_mode = METRIC_MODE_COMMIT
    else:
        _metric_mode = METRIC_MODE_RELEASE

    # if --start_date isn't specifid, fallback to a default date (Jan 1st 2015)
    if (args.start_date):
        _start_date = args.start_date
        print "devops-stats :: custom start date : " + str(_start_date)
    else:
        _start_date = DEFAULT_START_DATE
        print "devops-stats :: using default start date : " + str(_start_date)

    # if --project is set, check that --folder isn't specified
    if args.project:

        print "devops-stats :: <repo-dir> is a collection of git repos."

        if (args.folder): 
            sys.stderr.write("devops-stats :: ERROR: cannot specify '--folder' \
                if '--project' is used. aborting.")
            sys.exit(1)
        
        _mode = MODE_PROJECT

    else:
        # if --folder is set, check that --commit isn't set (not supported as of 
        # now)
        if (args.folder): 

            if (args.commit):
                sys.stderr.write("devops-stats :: ERROR: metric mode '--commit' \
                    not supported by '--folder' yet. aborting.")
                sys.exit(1)

            _mode = MODE_FOLDER

        else:
            _mode = MODE_GENERAL

    # set the variables pointing to the temp files (SANDBOX_DIR) and 
    # the main temp file (UPDATES_DATES_FILE)
    SANDBOX_DIR = args.out_dir
    UPDATES_DATES_FILE = SANDBOX_DIR + "/" + UPDATES_DATES_FILE

    pre_process(_mode, _metric_mode, args.repo_dir)
    plot(_mode, _metric_mode, args.repo_dir, _start_date)

