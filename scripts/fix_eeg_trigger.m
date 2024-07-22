function [EEG, err_report] = fix_eeg_trigger(EEG, TMPBEHAV, VERBOSE, TASK)
%Fix_EEG_Trigger fixes missing end trial or start trial triggers and
%removes ghost trigger that are not coded anywhere

%   Insert EEG set and behav data structure, output is fixed EEG
%   set.
[EEG.event.REPEAT] = deal(false);
[EEG.event.trial_num] = deal(0);

cnt = 1; % counter for EEG event data
trial = 1; % trial indicator for behavioral data.
trig_num = "";
fixed = 0;
err_report = {};
length_event_struct = length([EEG.event.trial_num]);
double_trigs_2_delete = {"S 10", "S 11", "S 20", "S 21", "S102", "S104", ...
    "S122", "S124", "S142", "S144", "S162", "S164", "S182", "S184", "S101", ...
    "S 12", "S 13", "S 92", "S 40", "S 41", "S 50", "S 51", "S 30", "S 31"};

while trial <= length(TMPBEHAV.trial_data) && cnt <= length_event_struct

    TMPBEHAV.trial_data{trial}.trial_num = trial;

    previous_trig_num = trig_num;
    trig_num = determine_trig_num(TMPBEHAV,trial);

    run = true;
    % check if we have a start and end trial here.
    while run && cnt <= length([EEG.event.trial_num])

        % Check for duplicate triggers
        for trig = 1:length(double_trigs_2_delete)
            % if this is a end trial trigger...
            if strcmp(EEG.event(cnt).type, double_trigs_2_delete{trig})
                % is there a second "S101" within three events?
                if any(strcmp({EEG.event(cnt+1:cnt+2).type}, double_trigs_2_delete{trig}))
                    % delete the second S101
                    idx = find(strcmp({EEG.event(cnt+1:cnt+2).type}, double_trigs_2_delete{trig}));
                    EEG.event(cnt+idx) = [];
                    str = strjoin(["deleted a duplicate ", double_trigs_2_delete{trig}, ...
                        " at position ", cnt], "");
                    fixed = fixed + 1;
                    err_report{fixed} = str;
                    if VERBOSE
                        disp(str)
                    end
                end
            end
        end
        %
        %         % if this is a end pause trigger...
        %         if strcmp(EEG.event(cnt).type, "S 21")
        %             % is there a second "S21" within three events?
        %             if any(strcmp({EEG.event(cnt+1:cnt+2).type}, "S 21"))
        %                 % delete the second S101
        %                 idx = find(strcmp({EEG.event(cnt+1:cnt+2).type}, "S 21"));
        %                 EEG.event(cnt+idx) = [];
        %                 str = strjoin(["deleted a duplicate S 21 at position ", cnt], "");
        %                 fixed = fixed + 1;
        %                 err_report{fixed} = str;
        %                 if VERBOSE
        %                     disp(str)
        %                 end
        %             end
        %         end
        % if this is a ghost trigger...
        if strcmp(EEG.event(cnt).type, "S160")
            EEG.event(cnt) = [];
            cnt = cnt - 1;
            % document fix
            str = strjoin(["S160 removed at position ", cnt], "");
            fixed = fixed + 1;
            err_report{fixed} = str;
            if VERBOSE
                disp(str)
            end
            % if this is a end startvec trigger...
            %         elseif strcmp(EEG.event(cnt).type, "S 13")
            %             % and the following is a start startvec tirgger...
            %             if strcmp(EEG.event(cnt+1).type, "S 12")
            %                 % this is a ghost and we delete it.
            %                 EEG.event(cnt+1) = [];
            %                 % document fix
            %                 str = strjoin(["S 12 removed at position ", cnt+1], "");
            %                 fixed = fixed + 1;
            %                 err_report{fixed} = str;
            %                 if VERBOSE
            %                     disp(str)
            %                 end
            %             else
            %                 cnt = cnt + 1;
            %             end

            % if this is a start startvec trigger...
        elseif strcmp(EEG.event(cnt).type, "S 12")

            % is there a second "S 12" within three events?
            if any(strcmp({EEG.event(cnt+1:cnt+2).type}, "S 12"))
                % delete the second S 12
                idx = find(strcmp({EEG.event(cnt+1:cnt+2).type}, "S 12"));
                EEG.event(cnt+idx) = [];
                str = strjoin(["deleted a duplicate S 12 at position ", cnt], "");
                fixed = fixed + 1;
                err_report{fixed} = str;
                if VERBOSE
                    disp(str)
                end
            end

            % THIS SECTION MIGHT CAUSE LOTS OF SUPERFLUOUS S 13!!
            % Cause sometimes there are multiple S 35 after S 12 first.
            % is not a "S 13" within five events? Or a "S 92"?
            if ~any(strcmp({EEG.event(cnt+1:cnt+4).type}, "S 13")) && ~any(strcmp({EEG.event(cnt+1:cnt+4).type}, "S 92"))
                % if so, add S 13 after S 12 with +750 ms latency
                tmp_event = [EEG.event];
                s13_lat = tmp_event(cnt).latency + 0.75*EEG.srate;
                tmp_event2 = [tmp_event(1:cnt+1), tmp_event(cnt+1:end)];
                tmp_event2(cnt+1).type = char("S 13");
                tmp_event2(cnt+1).code = char("INSERTED");
                tmp_event2(cnt+1).latency = s13_lat;
                EEG.event = tmp_event2;
                str = strjoin(["S 13 added at position ", cnt+1], "");
                fixed = fixed + 1;
                err_report{fixed} = str;
                if VERBOSE
                    disp(str)
                end
            end

            %  is there an end trial/start break trigger where it should be?
            if (trial == 1 || ...
                    strcmp(EEG.event(cnt-2).type, "S101") || ...
                    strcmp(EEG.event(cnt-2).type, "S 92") || ...
                    strcmp(EEG.event(cnt-2).type, "S 20") || ...
                    strcmp(EEG.event(cnt-2).type, "S 21"))

                % repeated trials, do not increase
                % trial count
                if cnt > 2 && strcmp(EEG.event(cnt-2).type, "S 92") % do not increase trial num if we have 92
                    EEG.event(cnt-1).trial_num = trial-1;
                    EEG.event(cnt-1).REPEAT = true;
                    cnt = cnt + 1;
                    prev_trial_start = cnt-1; % save index for next run.
                    if VERBOSE
                        str = strjoin(["added trial number and repeat marker at position ", cnt], "");
                        disp(str)
                    end
                    % add trial number for correctly finished trials,
                    % increase trial count, go to next trial
                elseif strcmp(EEG.event(cnt-1).type, trig_num) % increase trial num if we have 101 or 20
                    EEG.event(cnt-1).trial_num = trial;
                    cnt = cnt + 1;
                    prev_trial_start = cnt-1; % save index for next run.
                    if VERBOSE
                        disp(strjoin(["added trial number at position ", cnt], ""))
                    end
                    run = false;
                    % Something was weird...
                else
                    warning(strjoin(["Trial ", trial, "at postition ", ...
                        cnt-1, "in EEG does not match in EEG and behav data. " + ...
                        "Entered 0. Check EEG.event entry to see what went wrong and add to funciton."]))
                    EEG.event(cnt-1).trial_num = 0;
                    cnt = cnt + 1;
                    run = false;
                end % if repreat or correctly ended

            elseif cnt > 2 && strcmp(EEG.event(cnt-2).type, "S100") % if we have a ghost trigger...
                EEG.event(cnt-2).type = char("S101");
                EEG.event(cnt-2).code = char("REPLACED");
                str = strjoin(["S 100 replaced at position ", cnt], "");
                fixed = fixed + 1;
                err_report{fixed} = str;
                if VERBOSE
                    disp(str)
                end
            elseif cnt > 2 && strcmp(EEG.event(cnt-2).type, "S 98") % if we have a ghost trigger...
                EEG.event(cnt-2) = [];
                cnt = cnt - 1;
                str = strjoin(["S 98 removed at position ", cnt], "");
                fixed = fixed + 1;
                err_report{fixed} = str;
                if VERBOSE
                    disp(str)
                end
            elseif cnt > 2 && strcmp(EEG.event(cnt-2).type, "S 80") % if we have a ghost trigger...
                EEG.event(cnt-2) = [];
                cnt = cnt - 1;
                str = strjoin(["S 80 removed at position ", cnt], "");
                fixed = fixed + 1;
                err_report{fixed} = str;
                if VERBOSE
                    disp(str)
                end
                % if the previous trigger number is the same as the
                % current one in eeg but not the same in behav time
                % elapsed since last trial start is less than 8
                % s...
            elseif contains(TASK, 'D') && ...
                    strcmp(EEG.event(cnt-1).type, previous_trig_num) && ...
                    (EEG.event(cnt-1).latency - EEG.event(prev_trial_start).latency) < 10*EEG.srate 
                % we are apparently missing a trial repeat trigger
                tmp_event = [EEG.event];
                tmp_event2 = [tmp_event(1:cnt-2), tmp_event(cnt-2:end)];
                tmp_event2(cnt-1).type = char("S 92");
                tmp_event2(cnt-1).code = char("INSERTED");
                EEG.event(cnt-1).REPEAT = true;
                EEG.event = tmp_event2;
                str = strjoin(["S 92 added at position ", cnt], "");
                fixed = fixed + 1;
                err_report{fixed} = str;
                if VERBOSE
                    disp(str)
                end
            elseif strcmp(EEG.event(cnt-1).type, "S 92")
                % the trial identification trigger is apparently missing
                % after an incomplete trial
                tmp_event = [EEG.event];
                tmp_event2 = [tmp_event(1:cnt-1), tmp_event(cnt-1:end)];
                tmp_event2(cnt).type = previous_trig_num;
                tmp_event2(cnt).code = char("INSERTED");
                EEG.event = tmp_event2;
                str = strjoin(["trial identification trigger added after S 92 at position ", cnt], "");
                fixed = fixed + 1;
                err_report{fixed} = str;
                if VERBOSE
                    disp(str)
                end
            elseif strcmp(EEG.event(cnt-1).type, "S101")
                % the trial identification trigger is apparently missing
                % after a complete trial
                tmp_event = [EEG.event];
                tmp_event2 = [tmp_event(1:cnt-1), tmp_event(cnt-1:end)];
                tmp_event2(cnt).type = trig_num;
                tmp_event2(cnt).code = char("INSERTED");
                EEG.event = tmp_event2;
                str = strjoin(["trial identification trigger added after S101 at position ", cnt], "");
                fixed = fixed + 1;
                err_report{fixed} = str;
                if VERBOSE
                    disp(str)
                end
            else % we are apparently missing an end trial trigger.
                tmp_event = [EEG.event];
                tmp_event2 = [tmp_event(1:cnt-2), tmp_event(cnt-2:end)];
                tmp_event2(cnt-1).type = char("S101");
                tmp_event2(cnt-1).code = char("INSERTED");
                EEG.event = tmp_event2;
                str = strjoin(["S 101 added at position ", cnt], "");
                fixed = fixed + 1;
                err_report{fixed} = str;
                if VERBOSE
                    disp(str)
                end
            end % we have a end trial marker

            % if there is a match in trig_nums anyway...
        elseif cnt ~= 1 && strcmp(EEG.event(cnt-1).type, trig_num)
            % we are apparently missing an S 12.
            tmp_event = [EEG.event];
            tmp_event2 = [tmp_event(1:cnt-1), tmp_event(cnt-1:end)];
            tmp_event2(cnt).type = char("S 12");
            tmp_event2(cnt).code = char("INSERTED");
            EEG.event = tmp_event2;
            str = strjoin(["S 12 added at position ", cnt], "");
            fixed = fixed + 1;
            err_report{fixed} = str;
            if VERBOSE
                disp(str)
            end

        else
            cnt = cnt + 1;
        end % start startvec if
        length_event_struct = length([EEG.event.trial_num]);
    end % while
    trial = trial + 1;
end % trial


%% Fill in all the zeroes between trial starts with trial numbers

tmp_trial_nums = [EEG.event.trial_num];
[val, ind] = unique(tmp_trial_nums);
val2 = val(2:end); % do not need the 0
ind2 = [ind(2:end)', length(tmp_trial_nums)]; % do not need the 0 index but end of event vector.

for i = 1:length(ind2)-1
    tmp_trial_nums(ind2(i):ind2(i+1)-1) = val2(i);
end

tmp_trial_nums(end) = val2(i);

for ev = 1:length([EEG.event.trial_num])
    EEG.event(ev).trial_num = tmp_trial_nums(ev);
end

% fill in the last entries in the matrix with trial numbers
% EEG.event(ev:length([EEG.event.trial_num])).trial_num = tmp_trial_nums(ev);


%% Fill in all the zeroes in repeated trials with ones in REPEAT

repeat_idx = find([EEG.event.REPEAT]);

for rep = repeat_idx

    next = true;

    % within one trial loop: add true to each repeat until you hit the end
    % of the trial
    while next
        rep = rep + 1;
        EEG.event(rep).REPEAT = true;
        % once you hit the next end trial trigger
        if strcmp(EEG.event(rep).type, "S 92") | strcmp(EEG.event(rep).type, "S101")
            % quit loop
            next = false;
        end
    end
end


%% Look for duplicate trial start triggers

% ignore repeated trials since the trial num does not
% increase which would mess up the following algorithm.
tmp_event = [EEG.event];
tmp_event2 = tmp_event(~[tmp_event.REPEAT]);
trial_start_idx = find(diff([tmp_event2.trial_num]) > 0);
to_del = 1;
del_idx = [];

for trig = trial_start_idx

    s12_count = 0;
    s13_count = 0;
    next = true;

    % within one trial loop: add true to each repeat until you hit the end
    % of the trial
    while next

        % look for dupliacte start startvec trigger
        if strcmp(EEG.event(trig).type, "S 12")
            s12_count = s12_count + 1;
            if s12_count > 1
                del_idx(to_del) = trig;
                to_del = to_del + 1;
                str = strjoin(["S 12 deleted at position ", trig], "");
                fixed = fixed + 1;
                err_report{fixed} = str;
                if VERBOSE
                    disp(str)
                end
            end
        end

        % look for dupliacte end startvec trigger
        if strcmp(EEG.event(trig).type, "S 13")
            s13_count = s13_count + 1;
            if s13_count > 1
                del_idx(to_del) = trig;
                to_del = to_del + 1;
                str = strjoin(["S 13 deleted at position ", trig], "");
                fixed = fixed + 1;
                err_report{fixed} = str;
                if VERBOSE
                    disp(str)
                end
            end
        end
        % once you hit the next end trial trigger
        if strcmp(EEG.event(trig).type, "S 92") | strcmp(EEG.event(trig).type, "S101")
            % quit loop
            next = false;
        end
        trig = trig + 1;
    end
end

EEG.event(del_idx) = [];

end
