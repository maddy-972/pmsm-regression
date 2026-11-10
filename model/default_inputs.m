%% Default test inputs - each is [time, value]
% A repeated time point creates a clean step

% Speed reference: 0 -> 50 rad/s at 10 ms
w_ref_in = [0    0;
            0.01 0;
            0.01 50;
            1    50];

% Load torque: 0 -> 50 Nm at 0.5 s
TL_in = [0   0;
         0.5 0;
         0.5 50;
         1   50];

% Fault injection: offset on the measured iq [A] (0 = no fault)
iq_offset_in = [0 0;
                1 0];

t_stop = 1;