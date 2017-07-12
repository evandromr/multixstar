#! /usr/bin/env python
"""
based on the code pvm_xstar using multiprocessing module instead of pvm.

Written by Michael S. Noble (mnoble@space.mit.edu)
Copyright (c) 2008-2009, Massachusetts Institute of Technology

multixstar: Manages parallel execution of multiple XSTAR runs,
using the multiprocessing python module.
XSTAR is part of the LHEASOFT astronomy toolset from
HEASARC, and is used to for calculating the physical conditions and
emission spectra of photoionized gases (Kallman & Bautista 2001).
"""
from __future__ import print_function
from __future__ import division
from __future__ import unicode_literals
from __future__ import absolute_import
from six.moves import input
import argparse
import subprocess
import os
import multiprocessing as mp
import getopt
import datetime
import logging


__version__ = "0.1.1"


def run(cmd, env_setup="", stdout=True):
    '''runs cmds in systems shell.'''
    def return_stdout(p):
        return p.communicate()[0]
    if stdout:
        if not env_setup == "":  # if env is set then use it
            return return_stdout(subprocess.Popen(cmd, shell=True,
                                 executable=os.getenv("SHELL"),
                                 env=env_setup))
        return return_stdout(subprocess.Popen(cmd, shell=True,
                             executable=os.getenv("SHELL"),
                             stdout=subprocess.PIPE))
    else:
        if not env_setup == "":  # if env is set then use it
            return subprocess.Popen(cmd, shell=True,
                                    executable=os.getenv("SHELL"),
                                    stdout=subprocess.PIPE, env=env_setup,
                                    stdin=subprocess.PIPE)
        return subprocess.Popen(cmd, shell=True,
                                executable=os.getenv("SHELL"),
                                stdout=subprocess.PIPE, stdin=subprocess.PIPE)


def run_xstar(xcmd):
    to_return = ""
    os.chdir(xcmd[0])
    to_return += "Running:" + xcmd[0] + "\n"
    os.environ['PFILES'] = os.getcwd()
    to_return += "copycat" + "\n"
    subprocess.Popen("cp $HEADAS/syspfiles/xstar.par ./",
                     shell=True, executable=os.getenv("SHELL"),
                     stdout=subprocess.PIPE, env=os.environ).wait()
    p = subprocess.Popen("$FTOOLS/bin/" + xcmd[1], shell=True,
                         executable=os.getenv("SHELL"),
                         stdout=subprocess.PIPE, env=os.environ)
    to_return += str(p.pid) + "\n"
    output = p.stdout.readlines()
    os.chdir("../")
    to_return += "\n".join([line.decode("utf-8") for line in output]) + "\n"
    return to_return


def get_sufix(wdir, extra=""):
    ''' generates a unqie suffix'''
    dirlist = os.listdir(wdir)
    i = 1
    while True:
        if "mxstar." + str(i) + extra in dirlist:
                i += 1
        else:
            break
    return i


def process_flags(argv=None):
    '''
    processing script arguments
    '''
    usage = "multixstar [options] <joblist|params>"

    description = """multixstar: manages parallel execution of multiple XSTAR
    jobs, with python's multiprocessing module.
    Version: {version}""".format(version=__version__)

    epilogue = """Normally xstinitable will be launched to prompt for XSTAR
    physical parameters and generate a list of XSTAR jobs to run in parallel.
    This can be customized by supplying xstinitable parameters on the command
    line (such as mode=h) OR by supplying the name of an existing joblist
    file, in which case xstinitable will not be run nor will the generated
    spectra be collated into a single table model with xstar2table"""

    parser = argparse.ArgumentParser(usage=usage, description=description,
                                     epilog=epilogue)

    parser.add_argument("-w", "--workdir",
                        dest="workdir", default="./", metavar="WorkDir",
                        help="Work directory to save results of the run")
    parser.add_argument("-k", action="store_true", dest="keeplog",
                        default=False, help="keep log file",)
    parser.add_argument("-l", "--logfile",
                        dest="logfile", default="mxstar.log",
                        metavar="LOGFILE", help="specify file to save log")
    parser.add_argument("-n", "--nproc", type=int, dest="nproc", default=4,
                        metavar="NUMPROC",
                        help="Max number of processors per host")
    # options stores known arguments and
    # args stores potential xstinitable arguments
    options, args = parser.parse_known_args()

    ans = "blank"
    while not ans.lower()[0] == "y" and not ans.lower()[0] == "n":
        print("These values are being used: ")
        print("Working dir: ", options.workdir)
        print("Keep log file ?", options.keeplog)
        print("Log file: ", options.logfile)
        print("Max number of processor:", options.nproc)
        print("")
        ans = input("Would you like to continue? (y/n): ").strip()
        if not ans:
            ans = "blank"
    if ans.lower()[0] == "n":
        parser.print_help()
        os.sys.exit()
    else:
        workDir = os.path.abspath(options.workdir)
        keeplog = options.keeplog
        log_file = options.logfile
        max_process = options.nproc

    return max_process, workDir, args, log_file, keeplog


def check_ftools():
    """ checks that path to FTOOLS is defined"""
    if "FTOOLS" not in os.environ:
        raise OSError("$FTOOLS not set!\n please initialize HEASOFT and rerun")


def check_wdir(workDir):
    ''' checks that workDir exist and is writable
    '''
    # making new subdir to run in!!!!
    if os.path.isdir(workDir):
        open(workDir + "testing.test", "w")
        os.remove(workDir + "testing.test")
    else:
        raise IOError(workDir + " is not a dir!")


def get_xcmds(args=[], binpath=""):
    binpath += "/"
    # parameters required as arguments of xstinitable in order
    required = ["spectrum", "trad", "cfrac", "density", "rlrad", "column",
                "columnint", "columnsof", "columnnst", "rlogxi", "rlogxiint",
                "rlogxisof", "rlogxinst"]

    # separate required arguments from optional ones and sort required
    cmdargs_list = []
    psetargs = list(args)
    for arg in args:
        parname = arg.split("=")[0]
        if parname in required:
            cmdargs_list.append((required.index(parname), arg))
            psetargs.remove(arg)
    cmdargs_list.sort()
    cmdargs = " ".join([entry[1] for entry in cmdargs_list])

    if len(psetargs) > 0:
        if not os.path.exists("../" + psetargs[0]):
            to_return = "1" + "\n"
            # set xstinitable optional parameters with pset
            for arg in psetargs:
                run(binpath + "pset xstinitable " + str(arg), os.environ)
            # call xstinitable with ordered set of required parameters
            run(binpath + "xstinitable "+cmdargs, os.environ)
            joblist = "xstinitable.lis"
        else:
            if not args[0][0] == "/":
                to_return = "2" + "\n"
                joblist = args[0]
                os.rename("../" + joblist,
                          os.getcwd() + "/" + joblist.split("/")[-1])
                if joblist[-4:] == ".fits":
                    old1 = ".fits"
                    new1 = ".lis"
                else:
                    old1 = ".lis"
                    new1 = ".fits"
                os.rename("../" + joblist.replace(old1, new1),
                          os.getcwd() + "/" +
                          joblist.split("/")[-1].replace(old1, new1))
            else:
                os.rename(joblist, workDir + joblist.split("/")[-1])
                joblist = joblist.split("/")[-1]
    else:
        run(binpath + "xstinitable"+cmdargs, os.environ)
        joblist = "xstinitable.lis"
    return [x.strip("\n") for x in open(joblist, "r").readlines()]


def make_xcmd_dict(xcmds):
    # pad numbers
    padding = "%0" + str(len(str(len(xcmds)))) + "d"
    xcmd_dict = {}
    for n, x in enumerate(xcmds):
        padded = padding % (n + 1)
        xcmd_dict[padded] = x
    return xcmd_dict


def check_results(padded):
    fault = []
    for p in padded:
        if 'xout_spect1.fits' not in os.listdir(p):
            fault.append(p)
    fault.sort()
    return fault


def main(argv=None):
    # arg processing
    max_process, workDir, args, log_file, keeplog = process_flags()

    check_ftools()
    check_wdir(workDir)

    # Creates workDir/mxstar.X/
    wdir = "mxstar." + str(get_sufix(workDir))
    if not workDir[-1] == "/":
        workDir += "/"
    workDir += wdir
    os.mkdir(workDir)
    os.chdir(workDir)

    # create xstinitable list of parameters
    xcmds = get_xcmds(args, os.environ["FTOOLS"] + "/bin/")
    print(xcmds)
    # transform xstar parameters into dictionary
    xcmd_dict = make_xcmd_dict(xcmds)
    model_name = dict([z.split("=")for z in
                      xcmd_dict[list(xcmd_dict.keys())[0]].replace(
                      "xstar ", "").split()])["modelname"].replace(
                      "'", "").replace('"', '')
    if not os.path.exists(model_name):
        os.mkdir(model_name)
    os.chdir(model_name)

    # create a dir for each job
    for pad in xcmd_dict.keys():
        os.mkdir(pad)

    # setup logging
    logFormatter = logging.Formatter("%(message)s")
    rootLogger = logging.getLogger()

    fileHandler = logging.FileHandler(log_file)
    fileHandler.setFormatter(logFormatter)
    rootLogger.addHandler(fileHandler)

    consoleHandler = logging.StreamHandler(os.sys.stdout)
    consoleHandler.setFormatter(logFormatter)
    rootLogger.addHandler(consoleHandler)
    rootLogger.level = logging.INFO

    rootLogger.info("Using Dir " + os.getcwd())
    start_time = datetime.datetime.now()
    rootLogger.info("Start time: " + str(start_time))
    # end of loging setup

    print(xcmd_dict.items())
    # create pool of processes
    p = mp.Pool(processes=max_process)
    runs_return = p.map(run_xstar, xcmd_dict.items(), 1)

    for ret in runs_return:
        rootLogger.info(ret.replace("\n\n", "\n").strip())

    end_time = datetime.datetime.now()
    rootLogger.info("End time: " + str(end_time))

    failed = check_results(xcmd_dict.keys())
    if len(failed) == 0:
        for dest in ['xout_ain.fits', 'xout_aout.fits', 'xout_mtable.fits']:
            run("cp ../xstinitable.fits " + dest)
        padded = list(xcmd_dict.keys())
        padded.sort()
        for pad in padded:
            run("$FTOOLS/bin/xstar2table xstarspec=./" + pad +
                "/xout_spect1.fits", os.environ)
        if not keeplog:
            run("rm " + log_file)
    else:
        rootLogger.info("somethings not right in " + ",".join(str(failed)))


if __name__ == '__main__':
    main()
