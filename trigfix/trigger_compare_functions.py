from trigfix.globals import *
import ipywidgets as widgets

pd.options.mode.chained_assignment = None # just hide ennoying errors

# TODO debug define colors for trial types
trialtype_colors = {
    "trial_maintenance_right":      (0.3,   0.7,    0),
    "trial_maintenance_left":       (0.3,   1,      0),
    "trial_occlusion_cursor_right": (0,     0.7,    0.3),
    "trial_occlusion_cursor_left":  (0,     1,      0.3),
    "trial_occlusion_target_right": (0,     0.7,    0),
    "trial_occlusion_target_left":  (0,     1,      0),
    "trial_emulation_right":        (0.3,   0.7,    0.3),
    "trial_emulation_left":         (0.3,   1,      0.3),
    "trial_check_right":            (0.5,   0.7,    0.5),
    "trial_check_left":             (0.5,   1,      0.5),
    "trial_end":                    (0,     0,      0),
}

class BatchPosthocTriggerFix:
    def __init__(self, lab, inpath, outpath, samp_uncertainty=10, high_accuracy=False, only_middle=True, nth_best=1, allow_manual_mode=True, add_left_to_vmrk=False, diag_plot_1=True, diag_plot_2=False):
        self.lab = lab
        self.inpath = inpath
        self.outpath = outpath
        self.samp_unc = samp_uncertainty
        self.add_left = add_left_to_vmrk
        self.diag1, self.diag2 = diag_plot_1, diag_plot_2 # TODO diagplot 3, the match quantifier
        self.high_acc, self.middle, self.nth, self.allow_manual = high_accuracy, only_middle, nth_best, allow_manual_mode
        self.sfreq = get_param_from_excel("lab", lab, "sfreq")
        if lab == "Hagen":  self.get_all_matching_in_dir_Saskia() # TODO replace with general function
        else:               self.get_all_matching_in_dir()

    def valid_vmrk_naming_scheme(self, f):
        assert len(f.split("_")) in [3, 4], f"EmuError: vmrk files need to have the form \nEmu_group_sbjcode_task.vmrk or \nEmu_sbjcode_task.vmrk \n(checked file {f})\nPlease ensure ALL vmrk filenames in {self.inpath} follow this form."
        assert f.split("_")[-1].replace(".vmrk", "") in ["A", "B", "C", "D"], f"EmuError: task not found in vmrk filename {f}. Please ensure that ALL vmrk filenames in {self.inpath} follow the form Emu_group_sbjcode_task.vmrk or Emu_sbjcode_task.vmrk. (checked file {f})\nSplit the vmrks into the separate tasks if necessary."
        # TODO relax task assertion, if all tasks in file
        return True

    def get_all_matching_in_dir(self):
        all_vmrks = [f for f in os.listdir(self.inpath) if f.endswith(".vmrk") if self.valid_vmrk_naming_scheme(f)]
        all_npzs =  [f for f in os.listdir(self.inpath) if f.endswith(".npz")]
        
        # TODO replace Saskias code
        if self.lab == "Hagen":
            df_all_vmrks = pd.DataFrame(zip(
                [e.split("_")[0].lower() for e in all_vmrks],
                [e.split("_")[3] for e in all_vmrks],
                [""]*len(all_vmrks),
                all_vmrks),
            columns=["sbjcode", "task", "group", "vmrk_f"])
        else:
            df_all_vmrks = pd.DataFrame(zip(
                [e.split("_")[2].lower() for e in all_vmrks],
                [e.split("_")[3].replace(".vmrk", "") for e in all_vmrks],
                [e.split("_")[1] for e in all_vmrks],
                # [""]*len(all_vmrks),
                all_vmrks),
            columns=["sbjcode", "task", "group", "vmrk_f"])
        
        for e in all_npzs: 
            print(e) # TODO debug
            print(e.split("_")[-1].replace(".npz", "").lower())
            print(e.split("_")[1])
            print(e.split("_")[5])
        
        df_all_npzs = pd.DataFrame(zip(
            [e.split("_")[-1].replace(".npz", "").lower() for e in all_npzs],
            [e.split("_")[1] for e in all_npzs],
            [e.split("_")[5] for e in all_npzs],
            # [""]*len(all_npzs),
            all_npzs),
        columns=["sbjcode", "task", "group", "npz_f"])
        
        # display(df_all_npzs.head())
        # display(df_all_vmrks.head())

        self.matches_df = df_all_vmrks.merge(df_all_npzs, on=["sbjcode", "task", "group"], how="left")
        # display(self.matches_df)
        self.matches_df = self.matches_df.dropna()

        self.matches_df.to_excel(self.outpath/"match.xlsx")

    def get_all_matching_in_dir(self):
        # TODO remove function in release
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

        self.matches_df = df_all_vmrks.merge(df_all_npzs, on=["sbjcode", "task", "group"], how="left")

        self.matches_df = self.matches_df.dropna()

    def apply_fix_functions(self, row):
        log_eeg_match = Log_EEG_Match(
            row["vmrk_f"], row["npz_f"], 
            row["sbjcode"], row["task"], row["group"],
            self)
        log_eeg_match.run_fix_pipeline()
    
    def apply_fix(self, sbjcodes="all", tasks="all", groups="", only_warnings=True):

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
            if only_warnings:
                # try: 
                self.apply_fix_functions(row)
                # except Exception as e: print(f"EmuWarning for match {row['vmrk_f']}-{row['npz_f']}:\n{e}")
            else:
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
        if self.batch.lab == "Hagen": 
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
    
    # TODO: hide from release - maybe too identifying
    def adjust_special(self):
        if self.npz.is_special():
            self.dfs["npz"]["time"] = [t*10 for t in self.dfs["npz"]["time"]]
            self.batch.samp_unc = 200
        # # TODO REMOVE DEBUG!!!!!!!!!!!!!!!!!!!!!!
        # self.dfs["npz"]["time"] = [t*1.07 for t in self.dfs["npz"]["time"]] # 1.052

    def revert_special(self):
        if self.npz.is_special():
            self.out_df["time"] = [t/10 for t in self.out_df["time"]]
    
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
                           for part in ["vmrk", "npz"]) # note: end trigger
        n_npzt = len(trial_times["npz"])
        step = 0.01 if self.batch.high_acc else 0.1
        start = 0.25 if self.batch.middle else 0
        stop = 0.75 if self.batch.middle else 1
        npz_inds = [int(perc*n_npzt) for perc in np.arange(start, stop, step)] + [n_npzt - 1]
        for trialtvmrk in trial_times["vmrk"]:
            for npz_ind in npz_inds:#[ind_start_npz:ind_stop_npz]:
                adjust_npz = trialtvmrk - trial_times["npz"][npz_ind]
                adjusts.append(adjust_npz)
                adjust_matches.append(
                    abs(self.quantify_match(
                        trial_times["vmrk"], 
                        [e + adjust_npz for e in trial_times["npz"]]
                    )))
                
        # # TODO delete debug

        # plt.figure(facecolor="white", figsize=(20, 20))
        # plt.plot(adjust_matches, adjusts)
        # plt.show()

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

        nom   = len(trigs_only_vmrk) + len(trigs_only_npz) # TODO only_npz: overestimated with the double npz trigger situation in Hagen
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

        assert len(self.split_dfs["match_npz"]) == len(self.split_dfs["match_vmrk"]), f"EmuError: matched files are not same len; npz: {len(self.split_dfs['match_npz'])}; vmrk: {len(self.split_dfs['match_vmrk'])} - means function divide_dfs failed"
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

        def update(factor=1.0, offset=0.0):
            vlines_df_npz.set_xdata(df_npz["time"]*factor + offset)

        widgets.interact(
            update, 
            factor=widgets.FloatSlider(
                min=0, 
                max=2.0, 
                step=0.001, 
                value=1.0, 
                layout=slider_layout
            ), 
            offset=widgets.FloatSlider(
                min=-offset_max, 
                max=offset_max, 
                step=offset_max/10000, 
                value=0.0, 
                layout=slider_layout
            )
        )

    def plot_raw_without_matches(self, scale_order=4):
        # visual plotting of mismatches

        limit = 10**scale_order

        df_vmrk = self.dfs["vmrk"]
        df_npz = self.dfs["npz"]

        # TODO debug only keep trial starts:
        df_vmrk = df_vmrk[df_vmrk["label"].str.startswith("trial_")]
        df_npz = df_npz[df_npz["label"].str.startswith("trial_")]

        print(len(df_vmrk), len(df_npz))

        all_labels = list(set(df_vmrk["label"].tolist() + df_npz["label"].tolist()))

        f, ax = plt.subplots(1, 2, facecolor="white", sharey=True, figsize=(20, 2))

        # TODO debug remove list
        for l in all_labels:
            ax[0].vlines(df_vmrk[df_vmrk["label"] == l]["time"],  1, 2, color=trialtype_colors[l])
            ax[0].vlines(df_npz[df_npz["label"] == l]["time"], 0, 1, color=trialtype_colors[l])
        ax[0].set_xlabel("time in samples")

        ax[1].vlines(df_vmrk["time"][
            (df_vmrk["time"] < limit) &
            (df_vmrk["time"] > 0)
            ],  1, 2, color="black")
        ax[1].vlines(df_npz["time"][
            (df_npz["time"] < limit) &
            (df_npz["time"] > 0)
            ],  0, 1, color="green")
        ax[1].set_xlim([0, limit])
        ax[1].set_xlabel("time in samples")

        # if storename: plt.savefig(outpath/f'{Path(storename).stem}.png')
        plt.yticks([0.5, 1.5], ["npz", "vmrk"])

        plt.show()

    def get_correction_num(self):
        # note: correction factor must be ADDED
        matched_times = [self.split_dfs[f"match_{part}"]["time"].tolist() for part in ["npz", "vmrk"]]
        time_diffs = [npzt - vmrkt for npzt, vmrkt in zip(*matched_times)]

        if self.batch.diag2:
            plt.figure(facecolor="white")
            plt.plot(sorted(time_diffs))
            plt.show()

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

    def write_vmrk(self, out_df, vmrk_fname, lab="DD", suffix=""):
        # BIG TODO

        sfreq = {"DD": 500, "Hagen": 1000}[lab]
        sample_time_ms = {"DD": 2, "Hagen": 1}[lab]
        header = [
            f"Sampling rate: {sfreq}Hz, SamplingInterval: {sample_time_ms}ms",
            "Type, Description, Position, Length, Channel"
        ]
        file_lines = [l for l in header]
        for i, row in out_df.iterrows():
            file_lines.append(f"Stimulus, S{row['trig']:3d}, {row['time']}, 1, All")

        with open(outpath/f"{Path(vmrk_fname).stem}{suffix}.txt", "w") as f:
            f.writelines(l + "\n" for l in file_lines)

    def write_txt(self, out_df, out_fname, suffix=""):
        df = pd.DataFrame()
        
        # onset needs to be in seconds for eeglab (-.-)
        df["latency"] = [e/self.batch.sfreq for e in out_df["time"]]
        df["type"] = [f"S{round(e):3d}" for e in out_df["trig"]]
        df.to_csv(self.batch.outpath/f"{Path(out_fname).stem}{suffix}.txt", sep=",", index=None)

    def manual_optimizer(self, last_order=5):
        # replaces brute force
        # user inputs number, and then fit is shown
        self.plot_raw_without_matches(last_order)
        # self.batch.nth = int(input("enter a number by how much to shift: "))
        self.init_split_dfs()

        adjust_number = IntegerInput().get_value()

        last_order = len(str(adjust_number).replace("-", ""))
        self.adjust_npz_times(adjust_number, self.dfs["npz"]["time"])

        bad = self.divide_dfs()

        if adjust_number == 0: return True # possibility to quit

        self.diag_plot_mismatches(f"manual attempt") # TODO remove debug
        if bad: self.manual_optimizer(last_order) # TODO careful: infinite loop

    def brute_force(self):
        # print(f"EmuWarning: fixing failed initially for match for {self.npz_f}/{self.vmrk_f}; try brute force solution search in up to 10 attempts, might take a bit of time... (up to 10 times the previous solutions)") # TODO does this every time, don't know why
        orig_nth = self.batch.nth
        curr_nth = 0
        n_tries = 0
        bad = True
        n_attempts = 7
        if self.batch.allow_manual: n_attempts = 0

        while bad and n_tries < n_attempts: # TODO change back
            self.batch.nth = curr_nth
            self.init_split_dfs()

            self.adjust_npz_times_auto()
            bad = self.divide_dfs()

            curr_nth += 1
            n_tries += 1
        if bad:
            if self.batch.allow_manual:
                print(f"EmuWarning: could not fix mismatch of {self.npz_f}/{self.vmrk_f} with brute force in {n_attempts} attempts; going to manual mode")
                self.manual_optimizer_slider() # self.manual_optimizer()
            else:
                print(f"EmuWarning: mismatch of {self.npz_f}/{self.vmrk_f} not fixable with brute force in {n_attempts} attempts and no manual mode allowed; SUGGESTION: note down this subject and try again with other tweaks")
        self.batch.nth = orig_nth

    # until documentation: to understand code, start here, and then work backwards:
    def run_fix_pipeline(self):

        self.adjust_special() # *10 factor (TODO remove from release)
        bad = self.divide_dfs()
        if bad: self.brute_force() # try to auto-fix in case of bad
        if self.batch.diag1: self.diag_plot_mismatches(f"group {self.group}, subject: {self.sbjcode}, task {self.task}")
        self.output_all_but_ghosts() # inits self.out_df
        self.revert_special() # *10 factor (TODO remove from release)
        # TODO replace with vmrk instead of text
        self.write_txt(self.out_df, self.vmrk_f)
