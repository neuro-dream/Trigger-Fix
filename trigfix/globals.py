import trigfix
import os
from pathlib import Path
import pandas as pd
import numpy as np
import tkinter as tk
import matplotlib.pyplot as plt

###########################
#        Variables        #
###########################

root_path = Path(trigfix.__file__).parents[1]

df_eventtypes = pd.read_excel(root_path/"data"/"trigger_values.xlsx")

###########################
#        Functions        #
###########################

def translate_trig_num(trig_num):
    if trig_num in df_eventtypes["value"].tolist():
        trig_type = df_eventtypes[df_eventtypes["value"] == trig_num]["type"].tolist()[0]
        return trig_type
    else:
        return "__GHOST__"
    
def get_param_from_excel(ID_str, info_str):
    params_file = root_path/"data"/f"lab_parameters.xlsx"
    df = pd.read_excel(params_file)
    return df[df[df.columns.tolist()[0]] == ID_str][info_str].tolist()[0]

def parse_npz(npz, key):
    # npz can be either a filepath to the npz file, or a loaded npz
    if not type(npz) == np.lib.npyio.NpzFile:
        npz = np.load(npz, allow_pickle=True)

    assert key in ["lab_name", "parallel_port_id", "trigger_method", "distance_cm", "input_device", "refresh_rate", "with_practice", "eeg", "debug", "date_time", "sub_id", "experimenter", "window_res", "task_name", "repeats", "trigger", "time_since_init"], 'EmuError: key of parse_npz function must be one of either \n"lab_name", "parallel_port_id", "trigger_method", "distance_cm", "input_device", "refresh_rate", \n"with_practice", "eeg", "debug", "date_time", "sub_id", "experimenter", \n"window_res", "task_name", "repeats", "trigger", "time_since_init"'

    if key in ["lab_name", "parallel_port_id", "trigger_method", "distance_cm", "input_device", "refresh_rate", "with_practice", "eeg", "debug"]:
        out = npz["lab_params"].tolist()[key]
    elif key in ["date_time", "sub_id", "experimenter", "window_res"]:
        out = npz["dyn_params"].tolist()[key]
    elif key in ["task_name", "repeats"]:
        out = npz["task_params"].tolist()[key]
    else: #key in ["trigger", "time_since_init"]:
        out = npz["eeg_triggers"].tolist()[key]

    try: return eval(out)
    except: return out

###########################
#         Classes         #
###########################

class IntegerInput:
    def __init__(self):
        self.value = None
        self.create_window()

    def store_value(self):
        try:
            self.value = int(self.entry.get())
            self.root.destroy()
        except ValueError:
            pass

    def create_window(self):
        self.root = tk.Tk()
        self.root.title("Input Integer")

        instruction_label = tk.Label(self.root, text="Enter by how much integers you want the npz (green) lines to shift: ")
        instruction_label.pack()

        self.entry = tk.Entry(self.root)
        self.entry.pack()

        ok_button = tk.Button(self.root, text="OK", command=self.store_value)
        ok_button.pack()

    def get_value(self):
        self.root.mainloop()
        return self.value


# utilites for parsing event markers of output files
class MarkerDF():
    def __init__(self, fpath):
        self.fpath = fpath
        self.read_file()
        self.rename_columns()
        self.adjust_format()
        self.set_labels()
        self.drop_irrelevant_cols()
        
    def add_time_constant(self, const):
        self.df["time"] = [e + const for e in self.df["time"]]

    def set_labels(self):
        self.df["label"] = [translate_trig_num(e) for e in self.df["trig"]]

    def drop_irrelevant_cols(self):
        relevant_cols = ["trig", "time", "label"]
        self.df = self.df[relevant_cols]

class VmrkDF(MarkerDF):
    def __init__(self, fpath):
        super().__init__(fpath)

    def read_file(self):
        self.df = pd.read_csv(self.fpath, skiprows=12, header=None, error_bad_lines=False)

    def rename_columns(self):
        self.df = self.df[list(range(5))] # catch (rare) case that pd reads a sixth col with nans
        self.df.columns = [0, "trig", "time", 3, 4]

    def adjust_format(self):
        # adjust trigger format
        self.df = self.df.dropna() # drop the DC correction triggers

        # here, specify all non-experimental event labels that might occur in the recordings
        event_labels = ["boundary", "Buffer Overflow", "hi"]

        self.df = self.df[~self.df["time"].isin(event_labels)]
        self.df = self.df[~self.df["trig"].isin(event_labels)]
        self.df["trig"] = [int(e.replace("S", "")) for e in self.df["trig"]]

class EEGLabOutputDF(VmrkDF):
    def __init__(self, fpath):
        super().__init__(fpath)

    def read_file(self):
        self.df = pd.read_csv(self.fpath, error_bad_lines=False)

    def rename_columns(self):
        self.df.columns = ["time", "trig"]

class NpzDF(MarkerDF):
    def __init__(self, fpath, debug_plot=False, debug_data=None, debug_factor=1):
        self.npz = np.load(fpath, allow_pickle=True)
        self.npz_sfreq  = parse_npz(self.npz, "refresh_rate")
        self.task       = parse_npz(self.npz, "task_name")
        self.debug_plot, self.debug_data, self.debug_factor = debug_plot, debug_data, debug_factor
        super().__init__(fpath)
        self.scrape_filename_info()
    
    def read_file(self):
        trigger = self.npz["eeg_triggers"].tolist()["trigger"]
        times =   self.npz["eeg_triggers"].tolist()["time_since_init"]
        self.df = pd.DataFrame(zip(trigger, times))

    def rename_columns(self):
        self.df.columns = ["trig", "time"]

    def scrape_filename_info(self):
        self.sbjcode    = self.fpath.stem.split("_")[-1]
        self.task       = self.fpath.stem.split("_")[1]
        #TODO make nicer
        try:
            self.group      = self.fpath.stem.split("_")[5]
        except IndexError:
            pass#print("EmuWarning: no group found, probably because files from Hagen lab")
    
    def posthoc_add_checksound_triggers(self):

        # get all the time stamps of check trial trigger: 182 or 184
        check_trial_inds = self.df.loc[self.df["trig"].isin([182, 184])].index
        split_inds = [[curr, next] for curr, next in zip(check_trial_inds[:-1], check_trial_inds[1:])]
        split_inds += [[check_trial_inds[-1], len(self.df) - 1]]

        # put in separate dfs for easier handling
        dfs = [self.df.loc[curr_i:next_i, :] for curr_i, next_i in split_inds]

        # further sort out the dfs: (1) find first occurence of trial_end; (2) then _last_ traj start before this end
        occl_start_times, traj_start_times, incorrect_inds = [], [], []
        adj_dfs = []
        for ind, df in enumerate(dfs):
            try:
                end_ind = df[df["trig"] == 101].index[0]
                df = df.loc[df.index[0]:end_ind, :]
                adj_dfs.append(df) # for debug plot
                
                traj_start_inds = df[df["trig"] == 12].index
                last_trajstart_ind = traj_start_inds[-1]
                traj_start_times.append(df.loc[last_trajstart_ind, "npz_time"])

                occl_start_inds = df[df["trig"] == 30].index
                last_occlstart_ind = occl_start_inds[-1]
                occl_start_times.append(df.loc[last_occlstart_ind, "npz_time"])
            except IndexError as e: 
                incorrect_inds.append(ind)

        # get the other ingredient, the duration in npz frames of joystick_input
        check_trial_data = [trial for trial in self.npz["trial_data"] if trial["trial_type"] == "check"]
        # remove incorrect trials (probably terminated too early)
        # valid_check_trial_data = [trial for ind, trial in enumerate(check_trial_data) if not ind in incorrect_inds] # TODO issue solved if this line not included - but not quite sure why it makes sense - does npz auto-exclude checktrial triggers that were started again or sth?
        valid_check_trial_data = check_trial_data
        assert len(valid_check_trial_data) == len(adj_dfs), f"EmuError: {self.f}: \nnot same number of check trial data ({len(valid_check_trial_data)}) \nand traj starts ({len(adj_dfs)}) \n(sth went wrong) - matching not validly possible"
        conv_factor = self.debug_factor
        durs_until_checksound = [(len(data["joystick_input"]) - 2)*conv_factor for data in valid_check_trial_data] # TODO thoroughly check the number of frames (should not reduce effects though because if, then only small & constant shift)
        
        # then adjust accordingly with duration of joystick var
        new_rows = [
            {"trig": 186, "time": np.mean([t1+t3, t2])/self.npz_sfreq, "label": "check_sound"} 
            for t1, t2, t3 in zip(traj_start_times, occl_start_times, durs_until_checksound)]
        for row in new_rows: self.df = self.df.append(row, ignore_index=True)
        
        # sort, because, you never know
        self.df = self.df.sort_values(by="time")

        if self.debug_plot:
            
            for i, df in enumerate(adj_dfs):
                self.debug_plot_trial(df, durs_until_checksound[i], new_rows[i], self.debug_data[i])

    def plot_pipeline(self, data, ax):
        # TODO debug delete
        data_fields = ["pursuit", "traj", "joystick_input"]
        pursuit_x = list(range(len(data["pursuit"])))
        traj_x = list(range(len(data["traj"])))

        # for field in data_fields:
        #     data_t = np.transpose(data[field])
        #     ax.plot(data_t[1])
        data_t = np.transpose(data["traj"])
        ax.plot([t*self.debug_factor for t in traj_x], data_t[1])

        ax.plot(data["occlusion_switchframes_target"], data["occlusion_point"][1], color='red', marker="o")
        # ax.vlines(data["before_query"], -300, 300, color='red')
        ax.legend(data_fields)

    def debug_plot_trial(self, df, dur_until_checksound, new_row, debug_dat):

        trig12_time = df[df["trig"] == 12]["npz_time"].tolist()[0]

        factor_part1 = new_row["time"]-trig12_time
        factor_part2 = df[df["trig"] == 186]["npz_time"].tolist()[0]-trig12_time

        self.debug_factor = factor_part2/factor_part1

        colors = ["yellow", "black", "blue", "cyan", "orange", "red", "grey", "brown"]
        f, axx = plt.subplots(2, 1, facecolor="white", figsize=(12,2), sharex=True)
        # plt.figure(facecolor="white", figsize=(12,2))
        trigs = sorted(list(set(df["trig"])))
        print([(t, c) for t, c in zip(trigs, colors)])
        print(dur_until_checksound)
        for j, trig in enumerate(trigs):
            trig_times = df[df["trig"] == trig]["npz_time"]
            axx[0].vlines([t-trig12_time for t in trig_times], 0, 1, color=colors[j])
            # plt.vlines(trig_times, 0, 1, color=colors[j])
        axx[0].vlines((new_row["time"]-trig12_time), 0, 1, color="purple")
        self.plot_pipeline(debug_dat, axx[1]) # TODO debug delete
        plt.show()

    def is_special(self):
        # TODO remove from release
        query_ends = []
        query_ends += [f"HC_{e:03}" for e in [13,14,21,22,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,40,41]]
        query_ends += [f"ASD_{e:03}" for e in [1, 2]]
        return any([self.fpath.stem.endswith(e) for e in query_ends])

    def adjust_format(self):
        
        self.df["npz_time"] = [round(t*self.npz_sfreq) for t in self.df["time"]]

        if self.task == "D":
            try: self.posthoc_add_checksound_triggers()
            except Exception as e: print(e)

        # note: New lab *10 issue fix function remains in Log_EEG_Match class


