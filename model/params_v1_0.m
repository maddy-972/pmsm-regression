%% PMSM FOC parameters - release v1.0
% Motor
P.Rs   = 20e-3;    % stator resistance [Ohm]
P.Ld   = 400e-6;   % d-axis inductance [H]
P.Lq   = 1.2e-3;   % q-axis inductance [H]
P.psi  = 70e-3;    % PM flux linkage [Vs]
P.p    = 4;        % pole pairs
P.J    = 0.4;      % inertia [kg m^2]
P.B    = 0.01;     % viscous friction [Nm s/rad] (own assumption)

% Inverter / sampling
P.Udc  = 300;              % DC-link voltage [V]
P.fs   = 10e3;             % switching/sampling frequency [Hz]
P.Ts   = 1/P.fs;           % controller sample time [s]
P.Umax = P.Udc/sqrt(3);    % max phase voltage amplitude (linear SVM) [V]
P.Imax = 250;              % current limit [A]

% Current controller: technical optimum
% Plant delay: 1 Ts computation + 0.5 Ts PWM = 1.5 Ts
P.Tsig  = 1.5*P.Ts;
P.Kp_d  = P.Ld/(2*P.Tsig);     % = 1.33 V/A
P.Kp_q  = P.Lq/(2*P.Tsig);     % = 4.00 V/A
P.Ki_d  = P.Kp_d*P.Rs/P.Ld;    % = 66.7 V/(A s)
P.Ki_q  = P.Kp_q*P.Rs/P.Lq;    % = 66.7 V/(A s)

% Speed controller: placeholder, tuned in next step
P.Kp_w  = 0;
P.Ki_w  = 0;

% Simulation
P.Tsim  = 1e-5;    % fixed solver step [s] = Ts/10
model_version = "1.0";