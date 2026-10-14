# 阶段衔接、超算与结果检查

## 选择阶段

SCF → PH/DFPT → 组织 dyn/dvscf → 完整粗 k 网格波函数 → Wannier/粗电子声子数据 → 细网格插值/目标物性。可复用已经有效完成的阶段，不必重算全部流程；粗波函数阶段可选 nscf 或保留对称性的 bands，详见 qe-inputs.md。

- PH 使用 SCF 的数据与响应势。共用 scratch 时，NSCF 放在 PH 完成后，或为分支复制独立 SCF scratch。
- 以 prefix、结构、赝势、SCF/粗波函数截断与数据版本判断能否复用，不只看结束标记。
- 同一出发数据上比较 Wannier 与 QE 能带、速度、费米能和声子频率；既看粗网格，也看不参与拟合的点。比较费米能时先核对电子数、带子空间、占据/展宽和积分网格。粗/细费米能不一致要查原因；不能单纯强行固定 Ef 掩盖插值问题。
- 检查冻结窗口中每个 k 点的状态数不超过 nbndsub，目标能区是否被正确表示。投影、窗口和半芯排除不能仅从元素名称猜测。
- 整理 phonon 数据使用版本匹配的官方 pp.py/epw_pp.py 工具或明确检查过的脚本；其文件布局会随版本、池和计算模式变化。

## Slurm / scnet-hpc

先查看可用接口和环境。若有 list_environments/check_environment/preview_job，按需要选择 qe 或 epw，并在 submit_job 中传 environment；旧接口不支持时，不传未知参数，改为在已审阅作业脚本中明确初始化环境。

不在登录节点运行大型 QE/EPW 计算。准备 #SBATCH 资源、工作目录、输入/日志路径和失败返回码。环境初始化放在全部开头 #SBATCH 指令之后，计算命令之前。若原脚本另有 module purge/source，检查是否会覆盖所选环境。

工作目录以提交时明确指定的目录为准；相对 outdir/pseudo_dir/dvscf_dir 都据此解析。注意脚本里的 cd $SLURM_SUBMIT_DIR 可能抵消 --chdir；不要照抄到不同的提交工作目录。

EPW 5.8.1 要满足 npool×nimage=nproc；单 image 示例可用 mpirun -np "$SLURM_NTASKS" epw.x -nk "$SLURM_NTASKS" -in epw.in。这不意味着其他版本或其他阶段的最优池数相同。

MPI 在程序标题出现前失败时，先核对实际 mpirun、库和调度器启动集成，不立即重做物理输入。部分 Intel MPI 安装的调度器启动路径需要站点配置；若已确认只有单个分配节点，可在该节点验证厂商支持的 fork 启动方式，并显式指定已分配主机。它是针对启动问题的候选方案，不能推广到多节点，也不应写成所有算例的默认环境。

若用户授权运行，提交前核实脚本和资源，按稳定 request_id 去重。网络中断后先查队列/提交记录，不能盲目提交第二遍。Skill 本身不授予自动取消旧作业或覆盖计算目录的授权。

## 重启与结束判据

EPW 5.8.1 基本 Wannier 重启需要同时保留 epwdata.fmt、vmedata.fmt、crystal.fmt、prefix.epmatwp 和 prefix.ukk。先核对 epwread=.true.、wannierize=.false.，再检查与数据对应的版本、网格和带子空间。对于这些文件同目录、工作目录为该目录且 outdir='./' 的布局，可运行：

    python scripts/check_runtime.py checkpoint --directory /path/to/checkpoint --prefix demo

该工具只报告文件非空，不证明兼容性；其他路径布局及附加计算模式仍需查实际读入依赖。重做 Wannier 与读取 Wannier checkpoint 属于不同阶段；复用粗 Bloch epb 数据要核对原有池拆分。

Slurm 的 FAILED/ExitCode 记录整个作业脚本的结果。科学程序已经结束后，脚本里的检查或后处理仍可能失败，MCP 必须保留调度器原始状态。诊断时按顺序看最早错误、进程退出码、程序结束信息和后处理命令，不能只看日志最后一行，也不能把 FAILED 自动改称完成。

在运行命令旁记录返回码，保留单次进程的日志；下面的结构兼容 set -e：

```sh
rc=0
mpirun -np "$SLURM_NTASKS" epw.x -nk "$SLURM_NTASKS" -in epw.in > epw.out 2>&1 || rc=$?
printf '%s\n' "$rc" > epw.exitcode
exit "$rc"
```

可下载日志和退出码，在本机运行 check_runtime.py output --program epw --log epw.out --exit-code ACTUAL_CODE。不要将缺失的返回码填成 0，不把多次运行追加到同一日志后当作一次完成判断。

- EPW 5.8.1 的正常结束信息包含 Total program execution 以及 functionality-dependent EPW.bib file.，不要求 QE 的 JOB DONE。其他版本需另行核对，工具不会按旧规则自动接受。
- PW/PH 使用 JOB DONE 与实际进程退出码，并排查错误及未完成提示。PH 达到 max_seconds 可正常退出并保存可恢复数据，但请求的 DFPT 阶段尚未完成；沿用有效 checkpoint 按该版本恢复，不将受控停止作为完整结果。
- 运行检查通过只表示本工具覆盖的结束条件成立。Wannier 解缠与局域化有各自的收敛指标，需检查整个连续收敛窗口；最后一步 delta 很小不能替代连续迭代条件。

## 结果与输运

- 正常退出与结束标记只是运行检查的一部分；还要检查网格、电子展宽、响应势/插值、Wannier 收敛及目标量的收敛。
- 模式分辨负 λ/linewidth 或谱负值可能涉及 MP 负权重和数值误差；不能直接宣布为材料不稳定，也不能忽略。
- EPW 金属 res 文件的 μΩ·cm 换为 Ω·m 乘 10⁻⁸，σ=1/ρ。按该次文件头确认单位及展宽列。
- WF 电子热导估计：κe=L0 σT，L0=(π²/3)(kB/e)²≈2.4430×10⁻⁸ W·Ω/K²。标为近似，不是独立热流 BTE 结果，不包含晶格热导。
- 晶格热导通常还需要非谐力常数及声子输运；QE+EPW 的现有电阻率文件不能直接给出总热导率。
- 单一细网格不能证明收敛；粗/细费米能差异应结合能带插值和数值积分诊断，不将个别算例数值当作新任务的默认答案。
- 由电子自能转换寿命或输运率前，核对该版本 selfen.f90 的实际公式、写出变量和文件单位，区分 ImΣ、2ImΣ 与 ħ/τ。不能只按列标题猜因子，也不能直接把 meV 数值当作 s⁻¹；单粒子寿命与输运寿命还包含不同权重。

相关官方资料：
- https://docs.epw-code.org/Tutorials.html
- https://arxiv.org/abs/1604.03525
- https://slurm.schedmd.com/sbatch.html
- https://slurm.schedmd.com/sacct.html
- https://raw.githubusercontent.com/QEF/q-e/qe-7.3.1/EPW/src/stop_epw.f90
- https://raw.githubusercontent.com/QEF/q-e/qe-7.3.1/EPW/src/selfen.f90
- https://github.com/wannier-developers/wannier90/blob/v3.1.0/src/wannierise.F90
