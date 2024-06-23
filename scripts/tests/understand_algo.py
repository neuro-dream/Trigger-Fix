# this script was created to be used with strategically placed breakpoints that help the creator re-understand his own algorithm :)

import trigfix
from trigfix.trigger_compare_functions import *

# either put EEG and logfiles into emp_fpath below, or adjust the path.
emp_fpath = root_path/"data"/"inpath"
outpath   = root_path/"data"/"outpath"

batch = BatchPosthocTriggerFix(
    lab="EEG1",
    inpath=emp_fpath, 
    outpath=outpath,
    samp_uncertainty=20,
    mismatch_plot=True,
    allow_manual_mode=False
    )

batch.apply_fix(groups="all", tasks="A", sbjcodes="S31") #, sbjcodes="S14"