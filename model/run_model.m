function res = run_model(inp, param_file)
%RUN_MODEL  Run one test case of the PMSM FOC model.
%   res = run_model(inp)                 -> uses params_v1_0
%   res = run_model(inp, 'params_v1_1')  -> other release
%
%   inp fields: w_ref_in, TL_in, iq_offset_in  ([time value] arrays)
%               t_stop                         (scalar, s)
%   res fields: t + 10 signals on a common 100 us grid, version info

if nargin < 2, param_file = 'params_v1_0'; end
model = 'pmsm_foc';
here  = fileparts(mfilename('fullpath'));

% 1) Load parameters into this function's workspace (creates P, model_version)
run(fullfile(here, [param_file '.m']));

% 2) Configure the run without touching the base workspace
load_system(fullfile(here, [model '.slx']));
si = Simulink.SimulationInput(model);
si = si.setVariable('P',            P);
si = si.setVariable('w_ref_in',     inp.w_ref_in);
si = si.setVariable('TL_in',        inp.TL_in);
si = si.setVariable('iq_offset_in', inp.iq_offset_in);
si = si.setVariable('t_stop',       inp.t_stop);

% 3) Simulate
out = sim(si);
if ~isempty(out.ErrorMessage), error(out.ErrorMessage); end

% 4) Resample all signals onto one time grid (controller rate, 100 us)
t = (0:P.Ts:inp.t_stop)';
res.t = t;
names    = {'w_ref','wm','iq_ref','iq','iq_meas','id','ud','uq','Te','TL'};
discrete = {'iq_ref','ud','uq'};          % held signals -> zero-order hold
for k = 1:numel(names)
    n  = names{k};
    ts = out.logsout.get(n).Values;
    [tt, idx] = unique(ts.Time, 'last');
    dd = double(squeeze(ts.Data));
    dd = dd(idx);
    if any(strcmp(n, discrete)), m = 'previous'; else, m = 'linear'; end
    res.(n) = interp1(tt, dd, t, m, 'extrap');
end

% 5) Metadata for the regression report
res.version    = char(model_version);
res.param_file = param_file;
end