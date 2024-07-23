function EEG = delete_duplicates(EEG)
%DELETE_DUPLICATES Removes all duplicate triggers
%   This function finds all duplicate triggers and deletes the second one.

% generate list of triggers to check for duplicates
double_trigs_2_delete = {"S 10", "S 11", "S 20", "S 21", "S102", "S104", ...
    "S122", "S124", "S142", "S144", "S162", "S164", "S182", "S184", "S101", ...
    "S 12", "S 13", "S 92", "S 40", "S 41", "S 50", "S 51", "S 30", "S 31"};
cnt = 1; % coutner for EEG event data

% Check for duplicate triggers
for trig = 1:length(double_trigs_2_delete)
    % if this is a specific trigger...
    if strcmp(EEG.event(cnt).type, double_trigs_2_delete{trig})
        % is there a second specific trigger within three events?
        if any(strcmp({EEG.event(cnt+1:cnt+2).type}, double_trigs_2_delete{trig}))
            % delete the second specific trigger 
            idx = find(strcmp({EEG.event(cnt+1:cnt+2).type}, double_trigs_2_delete{trig}));
            EEG.event(cnt+idx) = [];
            str = strjoin(["deleted a duplicate ", double_trigs_2_delete{trig}, ...
                " at position ", cnt], "");
            disp(str)
        end
    end
end
cnt = cnt + 1;


end