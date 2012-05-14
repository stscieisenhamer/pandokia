
import os
import sys

# ignore some especially uninteresting clutter in the par files
# (you have to understand IRAF to understand why)
tdaIgnoreNames = ['mode','$nargs']
tdaIgnoreValues = ['none','no','','indef']

def run_pyraf_task( taskname, pfile, output_file="output_file", tda=None ) :
    import pyraf

    try :
        os.unlink(output_file)
    except OSError :
        pass

    sys.stdout.flush()
    sys.stderr.flush()

    if tda is None:
        tda = { }

    tda['taskname'] = taskname
    tda['pfile']    = pfile

    parobj=pyraf.irafpar.IrafParList(taskname, pfile)
    parlist=parobj.getParList()

    for k in parlist:
        if (k.name not in tdaIgnoreNames and
            str(k.value).strip().lower() not in tdaIgnoreValues):
            tda[k.name] = k.value
    command = getattr(pyraf.iraf, taskname)
    err = command( ParList=pfile, Stderr=output_file )
    if err :
        raise Exception("IRAF task %s exited with error %s"% (taskname, err) )


def run_process( arglist, env=None, output_file="output_file" ) :
    import subprocess

    sys.stdout.flush()
    sys.stderr.flush()

    if env is None :
        env = os.environ

    out = open(output_file, "w")

    p = subprocess.Popen( arglist, env = env, stdout=out, stderr=subprocess.STDOUT )
    status = p.wait()

    return status


def cat( *l ) :
    for x in l :
        f = open(x,"r")
        while 1 :
            b = f.read( 1048576 )
            if b == "" :
                break
            sys.stdout.write( b ) 
        f.close()