# Trigger-Fix
aligns and matches triggers from log file and EEG file

How to use:
- clone this repo
- adjust ```data/lab_parameters.xlsx``` if necessary: adding an entry with your lab-specific parameters.
- ```cd Trigger-Fix```
- create environment, once: ```conda env create --name trigfix-env --file environment.yml```
- activate environment: ```conda activate trigfix-env```
- install module: ```pip install -e .```
- run VS code to start the trigger fix (install [VS Code](https://code.visualstudio.com/download) first for this to work): ```code scripts/trigger_corr.ipynb```

Basic algorithm (flowchart; WIP)

```mermaid
%% (function: <a href='https://github.com/neurodream/Trigger-Fix/blob/main/trigfix/trigger_compare_functions.py#L92'>apply_fix</a>)

graph TD;
    A["<b>file selection:</b><br>- sbjcodes<br> - tasks<br> - groups"]
    B["<b>trigger sorting<br>into matched/unmatched:</b><br>for example illustration, see below"]
    C["<b>check if too many unmatched:</b><br>N_unmatched/N_matched > 20%?"]
    D["<b>fine-grained <br>temporal offsetting</b><br>vmrk against npz trigger list"]
    E["<b>fit value calculation:</b><br>average deviation of each element <br> in the shorter list <br>from the closest element <br>in the longer list"]
    F["<b>take nth best fit</b><br>default: 1st best fit"]
    G["<b>write new vmrk file</b>"]
    H["<b>visual inspection <br>(by user) <br>if still bad</b>"]
    I["<b>parameter tweaking:</b><br>- samp_uncertainty<br>- high_accuracy<br>- only middle<br>- nth_best<br>- ..."]

subgraph for_each_file_comb["for each npz-vmrk combination:"]
    direction TB
    B-->C;
    C-->|no|G;
    C-->|yes|D;
    subgraph for_each_offset["for each offset:"]
        direction TB
        E
    end
    D-->for_each_offset;
    for_each_offset-->F;
    F-->H;
    %% for_each_file_comb -- "until<br>all files<br>processed" --> for_each_file_comb;
    %% G--"until<br>all files<br>processed" --> for_each_file_comb;
    H-->|no|G;
    H-->|yes|I;
end

A--"batch <br>processing"-->for_each_file_comb;
%% I-->A;
```


Illustration of function ```sort_trigs_into_matched_unmatched```:

<img width="887" alt="trigger_sort_illustration_long" src="https://github.com/neurodream/Trigger-Fix/assets/117816806/6502e69c-d122-45f2-a09f-acb25a56a70d">
