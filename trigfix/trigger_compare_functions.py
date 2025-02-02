from trigfix.globals import *
import ipywidgets as widgets

pd.options.mode.chained_assignment = None # just hide ennoying errors

class BatchPosthocTriggerFix:
    def __init__(
            self,  
            inpath, 
            outpath,
            lab="Debug", 
            samp_uncertainty=10, 
            high_accuracy=False, 
            only_middle=True, 
            nth_best=1, 
            allow_manual_mode=True, # TODO rename to "slider mode" or similar
            add_left_to_vmrk=False, 
            mismatch_plot=True
            ):
        self.lab = lab
        self.inpath = inpath
        self.outpath = outpath
        self.samp_unc = samp_uncertainty
        self.add_left = add_left_to_vmrk
        self.diag1 = mismatch_plot
        self.high_acc, self.middle, self.nth, self.allow_manual = high_accuracy, only_middle, nth_best, allow_manual_mode
        self.sfreq = get_param_from_excel(lab, "sfreq")
        self.eeglab = get_param_from_excel(lab, "analysis") == "EEGLab"
        if self.eeglab:     self.get_all_matching_in_dir_eeglab()
        else:               self.get_all_matching_in_dir()

    def valid_vmrk_naming_scheme(self, f):
        assert len(f.split("_")) in [3, 4], f"TrigfixError: vmrk files need to have the form \nstudyname_group_sbjcode_task.vmrk or \nstudyname_sbjcode_task.vmrk \n(checked file {f})\nPlease ensure ALL vmrk filenames in {self.inpath} follow this form."
        assert f.split("_")[-1].replace(".vmrk", "") in ["A", "B", "C", "D"], f"TrigfixError: task not found in vmrk filename {f}. Please ensure that ALL vmrk filenames in {self.inpath} follow the form studyname_group_sbjcode_task.vmrk or studyname_sbjcode_task.vmrk. (checked file {f})\nSplit the vmrks into the separate tasks if necessary."
        # TODO relax task assertion, if all tasks in file
        return True

    def get_all_matching_in_dir(self):
        all_vmrks = [f for f in os.listdir(self.inpath) if f.endswith(".vmrk") if self.valid_vmrk_naming_scheme(f)]
        all_npzs =  [f for f in os.listdir(self.inpath) if f.endswith(".npz")]

        if len(all_vmrks) == 1 and len(all_npzs) == 1:

            df_all_vmrks = pd.DataFrame([("", "", "", all_vmrks[0])], columns=["sbjcode", "task", "group", "vmrk_f"])
            df_all_npzs  = pd.DataFrame([("", "", "", all_npzs[0])], columns=["sbjcode", "task", "group", "npz_f"])

        else:
        
            df_all_vmrks = pd.DataFrame(zip(
                [e.split("_")[2].lower() for e in all_vmrks],
                [e.split("_")[3].replace(".vmrk", "") for e in all_vmrks],
                [e.split("_")[1] for e in all_vmrks],
                # [""]*len(all_vmrks),
                all_vmrks),
            columns=["sbjcode", "task", "group", "vmrk_f"])
            
            df_all_npzs = pd.DataFrame(zip(
                [e.split("_")[-1].replace(".npz", "").lower() for e in all_npzs],
                [e.split("_")[1] for e in all_npzs],
                [e.split("_")[5] for e in all_npzs],
                # [""]*len(all_npzs),
                all_npzs),
            columns=["sbjcode", "task", "group", "npz_f"])

        self.matches_df = df_all_vmrks.merge(df_all_npzs, on=["sbjcode", "task", "group"], how="left")
        self.matches_df = self.matches_df.dropna()

        self.matches_df.to_excel(self.outpath/"match.xlsx")

    def get_all_matching_in_dir_eeglab(self):
        # TODO remove function in release & find a more flexible/inclusive approach of file matching
        all_vmrks = [f for f in os.listdir(self.inpath) if f.endswith("_fixed.txt")]
        all_npzs =  [f for f in os.listdir(self.inpath) if f.endswith(".npz")]

        df_all_vmrks = pd.DataFrame(zip(
            [e.split("_")[0].lower() for e in all_vmrks],
            [e.split("_")[3] for e in all_vmrks],
            [""]*len(all_vmrks),
            all_vmrks),
        columns=["sbjcode", "task", "group", "vmrk_f"])

        df_all_npzs = pd.DataFrame(zip(
            [e.split("_")[-1].replace(".npz", "").lower() for e in all_npzs],
            [e.split("_")[1] for e in all_npzs],
            [""]*len(all_npzs),
            all_npzs),
        columns=["sbjcode", "task", "group", "npz_f"])

        # make a case distinction if there is a session number - then also match on session
        len_splitted = [len(s.split("_")) for s in all_vmrks]
        assert len(set(len_splitted)) == 1, "TrigfixError: please ensure that all marker filenames in the input directory are of the same shape"
        
        # session number is included

        if len_splitted[0] == 6:
            # find npz pairs
            grouped_npz = df_all_npzs.groupby(["sbjcode", "task", "group"])
            assert len(set([len(g) for g in grouped_npz])) == 1 and len(list(grouped_npz)[0]) == 2, "TrigfixError: please ensure that there is exactly one npz file per session in the input folder"
            for name, group in grouped_npz:
                date = [row["npz_f"].split("_")[2] for i, row in group.iterrows()]
                group["date"] = date
                group = group.sort_values("date")
                group["session"] = ["1", "2"]
                df_all_npzs.loc[group.index, 'session'] = group["session"]
            # add a column for session number
            session_num = [e.split("_")[4] for e in all_vmrks]
            df_all_vmrks["session"] = session_num

            self.matches_df = df_all_vmrks.merge(df_all_npzs, on=["sbjcode", "task", "group", "session"], how="left")
            self.matches_df = self.matches_df.dropna()

        # session number is not included
        else:

            self.matches_df = df_all_vmrks.merge(df_all_npzs, on=["sbjcode", "task", "group"], how="left")
            self.matches_df = self.matches_df.dropna()

        self.matches_df.to_excel(self.outpath/"match.xlsx")

    def apply_fix_functions(self, row):
        log_eeg_match = Log_EEG_Match(
            row["vmrk_f"], row["npz_f"], 
            row["sbjcode"], row["task"], row["group"],
            self)
        log_eeg_match.run_fix_pipeline()
    
    def apply_fix(self, sbjcodes="all", tasks="all", groups=""):

        sub_df = self.matches_df.copy()
        
        # ensure that codes are lowercase
        if type(sbjcodes) == list: sbjcodes = [e.lower() for e in sbjcodes]
        else: sbjcodes = sbjcodes.lower()
        
        # sbjcodes selector
        if type(sbjcodes) == str:
            if not sbjcodes == "all": sub_df = sub_df[sub_df["sbjcode"] == sbjcodes]
        else: sub_df = sub_df[sub_df["sbjcode"].isin(sbjcodes)]

        # task selector
        if type(tasks) == str:
            if not tasks == "all": sub_df = sub_df[sub_df["task"] == tasks]
        else: sub_df = sub_df[sub_df["task"].isin(tasks)]
        # group selector
        if type(groups) == str:
            if not groups == "all": sub_df = sub_df[sub_df["group"] == groups]
        else: sub_df = sub_df[sub_df["group"].isin(groups)]

        # apply the fix
        for i, row in sub_df.iterrows():
            self.apply_fix_functions(row)

class Log_EEG_Match():
    def __init__(self, vmrk_f, npz_f, sbjcode, task, group, batch):
        self.vmrk_f = vmrk_f
        self.npz_f = npz_f
        self.sbjcode, self.task, self.group = sbjcode, task, group
        self.batch = batch # to derive batch variables, such as lab, sfreq etc.
        self.load_dfs()
        self.adjust_timing() # move npz unit (seconds) to EEG samples
        self.init_split_dfs()
        
    def load_dfs(self):
        # TODO move away from this lab hardcoding
        if self.batch.eeglab: 
            self.vmrk = EEGLabOutputDF(self.batch.inpath/self.vmrk_f)
            self.npz = NpzDF(self.batch.inpath/self.npz_f)
        else:                    
            self.vmrk = VmrkDF(self.batch.inpath/self.vmrk_f)
            self.npz = NpzDF(self.batch.inpath/self.npz_f)
        
        self.dfs = {"vmrk": self.vmrk.df, "npz": self.npz.df} # TODO remove this double usage
    
    def adjust_timing(self):
        # move npz to same units as EEG
        self.dfs["npz"]["time"] = [round(t*self.batch.sfreq) for t in self.dfs["npz"]["time"]]
        # capture npz triggers before the vmrk
        if self.batch.add_left:
            # get the difference
            first_npz_t  = self.dfs["npz"] ["time"].tolist()[0]
            first_vmrk_t = self.dfs["vmrk"]["time"].tolist()[0]
            diff = first_vmrk_t - first_npz_t
            self.dfs["vmrk"]["time"] = [e + diff for e in self.dfs["vmrk"]["time"]] # TODO logic problem

    def init_split_dfs(self):
        self.split_dfs = dict(zip(
            ["match_vmrk", "only_vmrk", "match_npz", "only_npz"],
            [pd.DataFrame(columns=self.dfs["vmrk"].columns) for _ in range(4)]
            ))
        
    def closest(self, val, l):
        # yoinked from: https://stackoverflow.com/a/12141207/6465789
        return min(l, key=lambda x:abs(x-val))

    def quantify_match(self, list1, list2):
        # TODO find a way that there are no "jumps" with translations - i.e. one can iteratively search
        # logic: average value of closest in each list
        # identify the shorter list
        if len(list1) > len(list2): longerl, shorterl = list1, list2
        else:                       longerl, shorterl = list2, list1
        # note: not standardized, so always compare against itself!
        # note: the lower, the better
        return abs(np.mean([self.closest(e, longerl) - e for e in shorterl]))

    def min_dev(self):
        # output vars
        adjusts, adjust_matches = [], []

        trial_times = dict([part, self.dfs[part][self.dfs[part]["trig"] == 101]["time"].tolist()] 
                           for part in ["vmrk", "npz"]) # note: 101 is trial end trigger
        n_npzt = len(trial_times["npz"])
        step = 0.01 if self.batch.high_acc else 0.1
        # focusing on middle triggers: hence ignores cases when EEG recording started too late and/or stopped too early
        start = 0.25 if self.batch.middle else 0
        stop = 0.75 if self.batch.middle else 1
        npz_inds = [int(perc*n_npzt) for perc in np.arange(start, stop, step)] + [n_npzt - 1] # TODO cannot understand this line anymore (24-06-23)
        for trialtvmrk in trial_times["vmrk"]:
            for npz_ind in npz_inds:#[ind_start_npz:ind_stop_npz]:
                adjust_npz = trialtvmrk - trial_times["npz"][npz_ind]
                adjusts.append(adjust_npz)
                adjust_matches.append(
                    abs(self.quantify_match(
                        trial_times["vmrk"], 
                        [e + adjust_npz for e in trial_times["npz"]]
                    )))

        return [adjusts, adjust_matches]

    def adjust_npz_times(self, adjust, orig_times):
        orig_times: self.dfs["time"] = orig_times
        self.dfs["npz"]["time"] = [e + adjust for e in orig_times]

    def adjust_npz_times_auto(self):
        orig_times = self.dfs["npz"]["time"].tolist()
        adjusts, adjust_matches = self.min_dev()
        df = pd.DataFrame(zip(adjusts, adjust_matches))
        df_adjusts = df.copy()
        df_adjusts.sort_values(by=1, inplace=True)
        df_adjusts.reset_index(inplace=True, drop=True)

        adjust = df_adjusts.iloc[self.batch.nth - 1, 0]
        return self.adjust_npz_times(adjust, orig_times)

    def move_heads(self, head_inds, out_dfs):

        # TODO use iloc
        head_types = [self.dfs[part]["trig"].tolist()[head_inds[part]] for part in ["vmrk", "npz"]]
        head_times = [self.dfs[part]["time"].tolist()[head_inds[part]] for part in ["vmrk", "npz"]]
        
        # case: trig and dist match
        rows = dict([part, self.dfs[part].iloc[head_inds[part],:]] for part in ["vmrk", "npz"])
        if head_types[0] == head_types[1] and abs(head_times[0] - head_times[1]) < self.batch.samp_unc:
            # append the rows to match
            for part in ["vmrk", "npz"]: 
                out_dfs[f"match_{part}"] = out_dfs[f"match_{part}"].append(rows[part])
                head_inds[part] += 1
        # one lags behind
        else:
            # vmrk lags behind: additional trigger
            if head_times[0] < head_times[1]:
                out_dfs["only_vmrk"] = out_dfs[f"only_vmrk"].append(rows["vmrk"])
                head_inds["vmrk"] += 1
            # npz lags behind: additional trigger
            else:
                out_dfs["only_npz"] = out_dfs[f"only_npz"].append(rows["npz"])
                head_inds["npz"] += 1

        return out_dfs, head_inds

    def is_bad(self):

        # ignore recording start/stop discordances via focusing only on middle trials
        start_time = self.split_dfs["only_npz"]["time"].tolist()[0]
        stop_time  = self.split_dfs["only_npz"]["time"].tolist()[-1]
        total_dur = stop_time - start_time

        trigs_only_vmrk = self.split_dfs["only_vmrk"][
            (self.split_dfs["only_vmrk"]["time"] > start_time + 0.2*total_dur) # &
            # (self.split_dfs["only_vmrk"]["time"] < stop_time  - 0.2*total_dur)
            ]
        trigs_only_npz = self.split_dfs["only_npz"][
            (self.split_dfs["only_npz"]["time"] > start_time + 0.2*total_dur) # &
            # (self.split_dfs["only_npz"]["time"] < stop_time  - 0.2*total_dur)
            ]
        trigs_match_vmrk = self.split_dfs["match_vmrk"][
            (self.split_dfs["match_vmrk"]["time"] > start_time + 0.2*total_dur) # &
            # (self.split_dfs["match_vmrk"]["time"] < stop_time  - 0.2*total_dur)
            ]

        nom   = len(trigs_only_vmrk) + len(trigs_only_npz)
        denom = len(trigs_match_vmrk)

        if denom == 0: return True # no matches found!

        return nom/denom > 0.2 # TODO identify factor empirically

    def divide_dfs(self):
        # TODO programmatically determine the sample_uncertainty (idea: iterative search of fitting linear function - but comput. intense)
        # output: dfs: match_vmrk, only_vmrk, match_npz, only_npz

        # TODO refine this naive implementation
        head_inds = {"vmrk": 0, "npz": 0}
        while all([head_inds[part] < len(self.dfs[part]) - 1 for part in ["vmrk", "npz"]]):
            self.split_dfs, head_inds = self.move_heads(head_inds, self.split_dfs)

        # TODO can't understand (state 24-06-23) why these are the same lengths; aren't there expected to be ghost triggers? 
        assert len(self.split_dfs["match_npz"]) == len(self.split_dfs["match_vmrk"]), f"TrigfixError: matched files are not same len; npz: {len(self.split_dfs['match_npz'])}; vmrk: {len(self.split_dfs['match_vmrk'])} - means function divide_dfs failed"
        return self.is_bad()
    
    def diag_plot_mismatches(self, title="", storename=None):
        # visual plotting of mismatches

        plt.figure(facecolor="white", figsize=(20, 2))

        # vmrk
        plt.vlines(self.split_dfs["only_vmrk"][self.split_dfs["only_vmrk"]["label"] != "__GHOST__"]["time"], 3, 4, color="red")
        plt.vlines(self.split_dfs["only_vmrk"][self.split_dfs["only_vmrk"]["label"] == "__GHOST__"]["time"], 3, 4, color="grey")
        
        # matches
        plt.vlines(self.split_dfs["match_vmrk"]["time"], 2, 3, color="black")
        plt.vlines(self.split_dfs["match_npz"]["time"],  1, 2, color="black")
        
        # npz
        plt.vlines(self.split_dfs["only_npz"]["time"], 0, 1, color="green")

        plt.title(title)
        plt.xlabel("time in samples")
        plt.yticks([0.5, 1.5, 2.5, 3.5], ["only npz", "match (npz)", "match (vmrk)", "only vmrk"])

        # if storename: plt.savefig(outpath/f'{Path(storename).stem}.png')

        plt.show()

    def manual_optimizer_slider(self):
        # for it to work, needs to call the cell magic %matplotlib widget at the top of the Jupyter cell!

        df_vmrk = self.dfs["vmrk"]
        df_npz = self.dfs["npz"]

        df_vmrk = df_vmrk[df_vmrk["label"].str.startswith("trial_")]
        df_npz = df_npz[df_npz["label"].str.startswith("trial_")]

        slider_layout = widgets.Layout(width='800px')
        offset_max = max([max(df_vmrk["time"]), max(df_npz["time"])])

        fig, ax = plt.subplots(figsize=(15, 2))
        vlines_df_vmrk, = ax.plot(df_vmrk["time"], [0]*len(df_vmrk), "|", color="black", markersize=100)
        vlines_df_npz, = ax.plot(df_npz["time"], [1]*len(df_npz), "|", color="green", markersize=100)
        ax.set_xlabel("time in samples")

        def update(factor=1.0, offset=0.0, fine_offset=0.0):
            vlines_df_npz.set_xdata(df_npz["time"]*factor + offset + fine_offset)

        factor_slider = widgets.FloatSlider(
            min=0, 
            max=2.0, 
            step=0.001, 
            value=1.0, 
            layout=slider_layout
        )
        offset_slider = widgets.FloatSlider(
            min=-offset_max, 
            max=offset_max, 
            step=0.5, 
            value=0.0, 
            layout=slider_layout
        )
        fine_offset_slider = widgets.FloatSlider(
            min=-1000, 
            max=1000, 
            step=0.001, 
            value=0.0, 
            layout=slider_layout
        )
        
        widgets.interact(update, factor=factor_slider, offset=offset_slider, fine_offset=fine_offset_slider)
            
    def get_correction_num(self):
        # note: correction factor must be ADDED
        matched_times = [self.split_dfs[f"match_{part}"]["time"].tolist() for part in ["npz", "vmrk"]]
        time_diffs = [npzt - vmrkt for npzt, vmrkt in zip(*matched_times)]

        if len(time_diffs) == 0: time_diffs = [0]
        return round(np.mean(time_diffs))

    def output_all_but_ghosts(self):
        # TODO saskias request (equivalent to function "output_only_npz")
        corr_num = self.get_correction_num()

        npz_df = self.split_dfs["only_npz"]

        npz_df["time"] = [e + corr_num for e in npz_df["time"]]
        npz_df = npz_df[npz_df["time"] >= 0]

        self.out_df = pd.concat([self.split_dfs["match_vmrk"], npz_df])
        
        self.out_df = self.out_df.sort_values("time")
        self.out_df = self.out_df[self.out_df["time"] >= 0]

    def output_only_npz(self):
        # TODO add the closest in vmrk of same type to really make sure there are no accidental doubles
        # output format agnostic - just times (in samples) and trig types in integer
        # remove all negatives
        # apply the individual correction factor

        corr_num = self.get_correction_num()
        out_df = self.split_dfs["only_npz"]
        out_df["time"] = [e + corr_num for e in out_df["time"]]
        out_df = out_df[out_df["time"] >= 0]

        return out_df

    def write_txt(self, out_df, out_fname, suffix=""):
        df = pd.DataFrame()
        
        # onset needs to be in seconds for eeglab (-.-)
        df["latency"] = [e/self.batch.sfreq for e in out_df["time"]]
        df["type"] = [f"S{round(e):3d}" for e in out_df["trig"]]
        df.to_csv(self.batch.outpath/f"{Path(out_fname).stem}{suffix}.txt", sep=",", index=None)

    def brute_force(self):
        # print(f"TrigfixWarning: fixing failed initially for match for {self.npz_f}/{self.vmrk_f}; try brute force solution search in up to 10 attempts, might take a bit of time... (up to 10 times the previous solutions)") # TODO does this every time, don't know why
        orig_nth = self.batch.nth
        curr_nth = 0
        n_tries = 0
        bad = True
        n_attempts = 7 # TODO parametrize?
        if self.batch.allow_manual: n_attempts = 0

        # TODO add tqdm update bar
        while bad and n_tries < n_attempts: # TODO change back
            self.batch.nth = curr_nth
            self.init_split_dfs()

            self.adjust_npz_times_auto()
            bad = self.divide_dfs()

            curr_nth += 1
            n_tries += 1
        if bad:
            if self.batch.allow_manual:
                print(f"TrigfixWarning: could not fix mismatch of {self.npz_f}/{self.vmrk_f} with brute force in {n_attempts} attempts; going to manual mode")
                self.manual_optimizer_slider() # self.manual_optimizer()
            else:
                print(f"TrigfixWarning: mismatch of {self.npz_f}/{self.vmrk_f} not fixable with brute force in {n_attempts} attempts and no manual mode allowed; SUGGESTION: note down this subject and try again with other tweaks")
        self.batch.nth = orig_nth

    # until documentation: to understand code, start here, and then work backwards:
    def run_fix_pipeline(self):

        bad = self.divide_dfs()
        if bad: self.brute_force() # try to auto-fix in case of bad
        if self.batch.diag1: self.diag_plot_mismatches(f"group {self.group}, subject: {self.sbjcode}, task {self.task}")
        self.output_all_but_ghosts() # inits self.out_df
        # TODO replace with vmrk instead of text
        self.write_txt(self.out_df, self.vmrk_f)
