#Nose-style tests for STSDAS tasks with file comparisons
#The task is run in a class setup method, and each file comparison
#is then a separate test.

#for file comparisons
from pandokia.helpers import filecomp

#for file cleanup
import os
import glob

import pyraf
from pyraf import iraf


class PyrafTest(object):

    @classmethod
    def setUpClass(cls):
        #Each test will override this method to set
        # the following
        cls.setdefs()
##      This method must define the taskname
##             cls.taskname='calcspec'
##      the par file
##              cls.parfile='calcspec1.par'
##      the output files to be compared
##             cls.cmplist = ['calcspec1.fits', 'calcspec1.stdout']
##      and the output files to be ignored
##             cls.cleanuplist = []

                
        #Clean them up
        cls.preclean()

        #Define the TDAs
        cls.init_tdas(parfile=cls.parfile)

        #Support okifying
        cls.tda['_okfile']=cls.parfile.replace('.par','.okify')
        cls.okfh = open(cls.tda['_okfile'], 'w')
        
        #Provide a hook for any other setup
        cls.pre_exec()
        
        #Run the task
        t=getattr(iraf,cls.taskname)
        t.run(ParList=cls.parfile,
              Stdout=cls.parfile.replace('.par','.stdout'))

    @classmethod
    def pre_exec(cls):
        #Hook for tests to override if desired
        pass
    
    @classmethod
    def init_tdas(cls, parfile):
        #Start the tdas off with the name of the parfile
        cls.tda = dict(parfile=parfile)

        #then extract the interesting parameters....
        parobj=pyraf.irafpar.IrafParList(cls.taskname, parfile)
        parlist=parobj.getParList()

        # ignore some especially uninteresting clutter in the par files
        # (you have to understand IRAF to understand why)
        tdaIgnoreNames = ['mode','$nargs']
        tdaIgnoreValues = ['none','no','','indef']

        #...and add them to the dict
        for k in parlist:
            if (k.name not in tdaIgnoreNames and
                str(k.value).strip().lower() not in tdaIgnoreValues):
                cls.tda[k.name]=k.value


        
    def checkfile(self, fname, comparator, **kwds):

        #Save what and how we're comparing
        self.tda['testfile']=fname
        self.tda['comparator']=comparator

        #Save what, if anything, we're ignoring
        for k in kwds:
            if k.startswith('ignore'):
                self.tda[k]=kwds[k]

        #Syntactic sugar for FITS keyword ignore
        if 'ignore_keys' in kwds:
            kwds['value_excl_list']=','.join(kwds.pop('ignore_keys'))
            

        #Then do the comparison
        filecomp.check_file(fname, comparator,
                            exc=True,       #Raise AssertionError if different
                            okfh=self.okfh, #Update okfile for failed tests
                            cleanup=True,   #Clean up output file for passed tests
                            **kwds)         #Keyword args understood by comparators

        
    @classmethod
    def preclean(cls):        
        for fname in cls.cmplist + cls.cleanuplist:
            if '*' in fname:
                for k in glob.glob(fname):
                    safedel(k)
            else:
                safedel(fname)



    @classmethod
    def tearDownClass(cls):
        #CLose the okfile
        cls.okfh.close()
        
        #Remove side effect files
        for fname in cls.cleanuplist:
            try:
                os.remove(fname)
            except OSError:
                pass

def safedel(fname):
    try:
        os.remove(fname)
    except OSError:
        pass #Probably isn't there. This could be smarter.
    
